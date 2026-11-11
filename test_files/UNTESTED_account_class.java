public class Account {

    static int customerNumber = 12345;
    static int pinNumber = 6789;
    static double checkingBalance = 1000.0;
    static double savingBalance = 500.0;

    public static int getCustomerNumber() {
        return customerNumber;
    }

    public static int getPinNumber() {
        return pinNumber;
    }

    public static double getCheckingBalance() {
        return checkingBalance;
    }

    public static double getSavingBalance() {
        return savingBalance;
    }

    public static void calcCheckingWithdraw(double amount) {
        checkingBalance -= amount;
    }

    public static void calcSavingWithdraw(double amount) {
        savingBalance -= amount;
    }

    public static void calcCheckingDeposit(double amount) {
        checkingBalance += amount;
    }

    public static void calcSavingDeposit(double amount) {
        savingBalance += amount;
    }

    public static void testCheckingWithdraw(double amount) {
        System.out.println("Текущий баланс (Checking): " + checkingBalance);
        System.out.println("Запрос на снятие: " + amount);

        if (amount <= 0) {
            System.out.println("Ошибка: некорректная сумма.");
        } else if (checkingBalance - amount >= 0) {
            calcCheckingWithdraw(amount);
            System.out.println("Успешно. Новый баланс: " + checkingBalance);
        } else {
            System.out.println("Ошибка: недостаточно средств.");
        }
    }

    public static void testCheckingDeposit(double amount) {
        System.out.println("Текущий баланс (Checking): " + checkingBalance);
        System.out.println("Запрос на пополнение: " + amount);

        if (amount <= 0) {
            System.out.println("Ошибка: некорректная сумма.");
        } else {
            calcCheckingDeposit(amount);
            System.out.println("Успешно. Новый баланс: " + checkingBalance);
        }
    }

    public static void main(String[] args) {
        System.out.println("=== Тестирование банковского аккаунта ===");
        System.out.println("Номер клиента: " + customerNumber);

        // 1. Успешное снятие 200
        testCheckingWithdraw(200.0);

        // 2. Попытка снять 1500 (больше, чем есть)
        testCheckingWithdraw(1500.0);

        // 3. Попытка внести отрицательную сумму
        testCheckingDeposit(-50.0);

        // 4. Успешное пополнение на 500
        testCheckingDeposit(500.0);

        System.out.println("Финальный баланс: " + checkingBalance);
    }
}