import numpy as np
import pandas as pd
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
import os

data = pd.read_csv('data.csv', index_col=0)

'''
We recommend that you change your train and test split
'''

TRAIN, TEST = train_test_split(data, test_size=0.2, shuffle=False)


class Allocator():
    def __init__(self, train_data):
        '''
        Anything data you want to store between days must be stored in a class field
        '''

        self.running_price_paths = train_data.copy()

        self.train_data = train_data.copy()

        # Do any preprocessing here -- do not touch running_price_paths, it will store the price path up to that data

    def calculate_returns_covariance(self, window1=1000, window2=0):
        # Extract price data for the last 'window' ticks
        price_data = self.running_price_paths[-window1:-window2]

        # Calculate returns
        returns = np.diff(price_data, axis=0) / price_data[:-1]

        # Calculate covariance matrix
        covariance_matrix = np.cov(returns.T)
        # print(returns)

        return returns, covariance_matrix

    def objective_function(self, weights, returns, risk_free_rate):
        # Calculate portfolio return
        portfolio_return = np.sum(weights * np.mean(returns, axis=0))

        # Calculate portfolio volatility
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(self.covariance_matrix, weights)))

        # Calculate Sharpe Ratio
        sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility

        return -sharpe_ratio  # Minimize negative Sharpe Ratio

    def allocate_portfolio(self, asset_prices):
        '''
        asset_prices: np array of length 6, prices of the 6 assets on a particular day
        weights: np array of length 6, portfolio allocation for the next day
        '''
        print(len(self.running_price_paths))
        self.running_price_paths = self.running_price_paths._append(asset_prices, ignore_index=True)

        # ### TODO Implement your code here
        returns, self.covariance_matrix = self.calculate_returns_covariance(100, 10)
        num_securities = returns.shape[1]
        initial_weights = np.ones(num_securities) / num_securities

        # Define optimization constraints
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})  # Sum of weights equals 1

        result = minimize(self.objective_function, initial_weights, args=(returns, 0.0),
                          constraints=constraints, bounds=[(-1, 1)] * num_securities)

        return result.x


def grading(train_data, test_data):
    '''
    Grading Script
    '''
    weights = np.full(shape=(len(test_data.index), 6), fill_value=0.0)
    alloc = Allocator(train_data)
    for i in range(0, len(test_data)):
        weights[i, :] = alloc.allocate_portfolio(test_data.iloc[i, :])
        if np.sum(weights < -1) or np.sum(weights > 1):
            raise Exception("Weights Outside of Bounds")

    capital = [1]
    for i in range(len(test_data) - 1):
        shares = capital[-1] * weights[i] / np.array(test_data.iloc[i, :])
        balance = capital[-1] - np.dot(shares, np.array(test_data.iloc[i, :]))
        net_change = np.dot(shares, np.array(test_data.iloc[i + 1, :]))
        capital.append(balance + net_change)
    capital = np.array(capital)
    returns = (capital[1:] - capital[:-1]) / capital[:-1]

    if np.std(returns) != 0:
        sharpe = np.mean(returns) / np.std(returns)
    else:
        sharpe = 0

    return sharpe, capital, weights


sharpe, capital, weights = grading(TRAIN, TEST)
# Sharpe gets printed to command line
print(sharpe)

plt.figure(figsize=(10, 6), dpi=80)
plt.title("Capital")
plt.plot(np.arange(len(TEST)), capital)
plt.show()

plt.figure(figsize=(10, 6), dpi=80)
plt.title("Weights")
plt.plot(np.arange(len(TEST)), weights)
plt.legend(TEST.columns)
plt.show()