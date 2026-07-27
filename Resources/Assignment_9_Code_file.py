
import math

class BankAccount:
    def __init__(self, balance):
        if balance < 0:
            raise ValueError("Invalid balance")
        self.balance = balance

    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("Invalid deposit")
        self.balance += amount
        return self.balance

    def withdraw(self, amount):
        if amount <= 0:
            raise ValueError("Invalid withdraw")
        if amount > self.balance:
            raise Exception("Insufficient funds")
        self.balance -= amount
        return self.balance

def calculate_tax(income, age):
    if income < 0:
        raise ValueError("Invalid income")

    if income <= 250000:
        tax = 0
    elif income <= 500000:
        tax = income * 0.05
    elif income <= 1000000:
        tax = income * 0.1
    else:
        tax = income * 0.2

    if age > 60:
        tax *= 0.9

    return round(tax, 2)
