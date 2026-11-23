#include <iostream>
#include <string>

using namespace std;

// --- Прототипы функций ---
int getCustomerNumber();
int getPinNumber();
double getCheckingBalance();
double getSavingBalance();
void calcCheckingWithdraw(double amount);
void calcSavingWithdraw(double amount);
void calcCheckingDeposit(double amount);
void calcSavingDeposit(double amount);
void testCheckingWithdraw(double amount);
void testCheckingDeposit(double amount);

// --- Состояние (переменные) ---
int customerNumber = 12345;
int pinNumber = 6789;
double checkingBalance = 1000.0;
double savingBalance = 500.0;

int getCustomerNumber()
{
    return customerNumber;
}

int getPinNumber()
{
    return pinNumber;
}

double getCheckingBalance()
{
    return checkingBalance;
}

double getSavingBalance()
{
    return savingBalance;
}

void calcCheckingWithdraw(double amount)
{
    checkingBalance -= amount;
}

void calcSavingWithdraw(double amount)
{
    savingBalance -= amount;
}

void calcCheckingDeposit(double amount)
{
    checkingBalance += amount;
}

void calcSavingDeposit(double amount)
{
    savingBalance += amount;
}

void testCheckingWithdraw(double amount)
{
    (std::cout << std::boolalpha << "Текущий баланс (Checking): " << checkingBalance << std::endl);
    (std::cout << std::boolalpha << "Запрос на снятие: " << amount << std::endl);
    if ((amount <= 0))
    {
        (std::cout << std::boolalpha << "Ошибка: некорректная сумма." << std::endl);
    }
    else
    {
        if (((checkingBalance - amount) >= 0))
        {
            calcCheckingWithdraw(amount);
            (std::cout << std::boolalpha << "Успешно. Новый баланс: " << checkingBalance << std::endl);
        }
        else
        {
            (std::cout << std::boolalpha << "Ошибка: недостаточно средств." << std::endl);
        }
    }
}

void testCheckingDeposit(double amount)
{
    (std::cout << std::boolalpha << "Текущий баланс (Checking): " << checkingBalance << std::endl);
    (std::cout << std::boolalpha << "Запрос на пополнение: " << amount << std::endl);
    if ((amount <= 0))
    {
        (std::cout << std::boolalpha << "Ошибка: некорректная сумма." << std::endl);
    }
    else
    {
        calcCheckingDeposit(amount);
        (std::cout << std::boolalpha << "Успешно. Новый баланс: " << checkingBalance << std::endl);
    }
}

int main()
{
    (std::cout << std::boolalpha << "=== Тестирование банковского аккаунта ===" << std::endl);
    (std::cout << std::boolalpha << "Номер клиента: " << customerNumber << std::endl);
    testCheckingWithdraw(200.0);
    testCheckingWithdraw(1500.0);
    testCheckingDeposit((-50.0));
    testCheckingDeposit(500.0);
    (std::cout << std::boolalpha << "Финальный баланс: " << checkingBalance << std::endl);
    return 0;
}
