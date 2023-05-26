from types import SimpleNamespace
import numpy as np
from scipy import optimize

class hair_salon():

    def __init__(self,do_print=True):
        """ initialize the model """

        if do_print: print('initializing the model:')

        self.par = SimpleNamespace() # create simplenamespace for parameters
        self.sol = SimpleNamespace() # create simplenamespace for solutions
        self.sim = SimpleNamespace()

        if do_print: print(f'calling .setup()\n')
        self.setup() # calls setup function, defined below

    def setup(self):
        """ setups baseline parameters """

        par = self.par
        sol = self.sol
        sim = self.sim

        # static model parameters
        par.eta = 0.5 # elasticity of demand
        par.w = 1.0 # hairdresser wage
        par.kappa_vec = np.linspace(1.0,2.0,2)

        # static model simulation vectors
        sim.kappa = 2.0 # kappa
        sim.l_vec = np.linspace(0.000000000001,5,100) # vector of l
        sim.profit_vec = np.zeros(sim.l_vec.size) # simulated vector of profits

        # static model solution vectors
        sol.l_vec = np.zeros(par.kappa_vec.size) # vector of optimal l
        sol.el_vec = np.zeros(par.kappa_vec.size) # vector of optimal expected l
        sol.profit_vec = np.zeros(par.kappa_vec.size) # vector of optimal profit

        # dynamic model parameters
        par.rho = 0.9
        par.sigma = 0.1 # std. dev. of random component of demand shocks
        par.iota = 0.01 # fixed adjusment cost for hiring or firing
        par.R = (1+0.01)**(1/12) # monthly discout factor
        par.kappa_init = 1 # initial kappa
        par.l_init = 0.0 # initial l
        par.T = 120 # number of periods
        par.K = 500 # number of random schock series
        par.epsilon = 1.0 # random component of demand shocks


    def calc_profit(self,l,k):
        """ calculate profit """

        par = self.par
        sol = self.sol

        # a. profit components
        price = k*(l**-par.eta) # implied price
        revenue = price*l
        payroll = par.w*l
        
        return revenue - payroll # profit
    
    
    def value_of_choice(self,l,k):
        """ calculate value of choice """

        return -self.calc_profit(l,k)
    
    
    def expected_optimal_l(self,k):
        """ calculate expected optimal l """
            
        par = self.par
        sol = self.sol
            
        return ((1-par.eta)*k/par.w)**(1/par.eta)
    
    
    def solve(self,do_print=True):
        """ solve model """
        
        par = self.par
        sol = self.sol
        opt = SimpleNamespace()
        
        guess = 0.5 # initial guess
        bound = (0.000000000001,100000000000000) # bounds for l

        # b. calculate profit
        for i, k in enumerate(par.kappa_vec):
            opt.l = optimize.minimize_scalar(self.value_of_choice, guess, bounds=bound, method='bounded', args=(k)).x
            
            # append solution vectors
            sol.l_vec[i] = opt.l # store optimal l value in the solution vector
            sol.profit_vec[i] = self.calc_profit(opt.l,k) # store optimal profit in the solution vector
            sol.el_vec[i] = self.expected_optimal_l(k) # store expected optimal l in the solution vector

            print(f'For kappa = {par.kappa_vec[i]:6.3f}: l = {sol.l_vec[i]:6.3f}, profit = {sol.profit_vec[i]:6.3f}, expected l = {sol.el_vec[i]:6.3f}')

            assert np.isclose(sol.l_vec[i],sol.el_vec[i]), 'l and expected l are not close' # check that l and expected l are close
            assert sol.l_vec[i] > 0, 'l is negative' # check that l is positive
        
        print('\nl and expected l are close and l is positive')
            
    
    def plot_profit(self):
        """ plot profit """

        import matplotlib.pyplot as plt

        par = self.par
        sol = self.sol
        sim = self.sim

        for i, k in enumerate(par.kappa_vec):
            for j, l in enumerate(sim.l_vec):
                sim.profit_vec[j] = self.calc_profit(l,k)    
            # a. plot
            fig = plt.figure()
            ax = fig.add_subplot(1,1,1)
            ax.plot(sim.l_vec,sim.profit_vec)
            ax.plot(sol.l_vec[i],sol.profit_vec[i],'o')
            ax.set_xlabel(r'$\ell_t$')
            ax.set_ylabel(r'$\pi_t$')
            ax.legend([r'$\pi(l)$',r'$\pi(l^*)$'])
            ax.set_title(f'Profit wrt. $\ell_t$, for $\kappa_t={k}$')
            ax.grid(True)

    
    def AR1_demand_shock(self,k):
        """ AR1 demand shock process """

        par = self.par 
        sim = self.sim

        # print(f'calling .AR1_demand_shock()')
        print(f'epsilon = {par.epsilon}')
        # print(f'rho = {par.rho}, k-1 = {k}, epsilon = {par.epsilon}')

        demand_shock = par.rho*k*np.exp(par.epsilon)

        print(f'demand shock = {demand_shock}')
        
        return demand_shock


    def period_value(self,lv,l,k,t,par):
        """ calculate ex-post period calue """

        if lv[t]==lv[t-1]:
            x = 0
        else:
            x = par.iota
        
        period_value = k*(l**(1-par.eta))-par.w*l-x
        discounting = par.R**-t

        # print(f'\nTypes: R^-t = {type(par.R**-t)}, second_par= {type(k*(l**(1-par.eta))-par.w*l-x)}, R = {type(par.R)}, t = {type(t)}, l = {type(l)}, k = {type(k)}, eta = {type(par.eta)}, w = {type(par.w)}, x = {type(x)}')
        # print(f'{np.asarray(par.R**-t)*[k*(l**(1-par.eta))-par.w*l-x]}')
        # print(f'Type of solution = {type(np.asarray(par.R**-t)*[k*(l**(1-par.eta))-par.w*l-x])}')
        
        return discounting * period_value
    

    def H(self):
        """ calculate H """

        par = self.par
        sol = self.sol
        sim = self.sim

        sol.dyn_l_vec = np.zeros(par.T) # initialize vector of l dynamic solutions
        sol.dyn_k_vec = np.zeros(par.T) # initialize vector of kappa dynamic solutions

        # a. ex-post and ex-ante values
        sol.H_plus = 0.0 # initialize ex-ante expected values
        sol.h_plus = np.zeros(par.K) # initialize vector of ex-post period values (h)

        for k in range(par.K): # loop over number of random shock series (simulations)
            
            print(f'\n**********************************************************************************************') 
            print(f'Simulation {k} of {par.K}')
            print(f'**********************************************************************************************') 

            for t in range(par.T): # loop over periods
                
                print(f'\nt = {t}')
                par.epsilon = np.random.normal(-0.5*par.sigma**2,par.sigma) # draw random part of the demand shock
                
                if t == 0: # if first period:
                    
                    sol.dyn_k_vec[t] = self.AR1_demand_shock(par.kappa_init) # calculate kappa for period 0

                else: # if not first period:
                    
                    sol.dyn_k_vec[t] = self.AR1_demand_shock(sol.dyn_k_vec[t-1]) # calculate kappa for period t
                
                # print(f'\nsol.dyn_k_vec[t] = {sol.dyn_k_vec[t]}, type = {type(sol.dyn_k_vec[t])}')

                sol.dyn_l_vec[t] = self.expected_optimal_l(sol.dyn_k_vec[t]) # calculate expected optimal l for period t
                
                # print(f'sol.dyn_l_vec[t] = {sol.dyn_l_vec[t]}, typer = {type(sol.dyn_l_vec[t])}')

                # b. append ex-post period values
                period_value = self.period_value(sol.dyn_l_vec,sol.dyn_l_vec[t],sol.dyn_k_vec[t],t,par) # calculate value for period t
                print(f'{t}th period value = {period_value }')
                
                sol.h_plus[k] += period_value # append period value to k'th simulation lifetime value
            
            print(f'\n>>> ex-post lifetime value (h) for {k}th simulation = {sol.h_plus[k]:6.3f}')

        sol.H_plus = np.sum(sol.h_plus)/par.K # calculate ex-ante expected value
        print(f'*** ex-ante expected lifetime value (H) = {sol.H_plus:6.3f} *** \n')
