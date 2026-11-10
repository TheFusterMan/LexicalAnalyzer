public class LogicCheck {
    public static void main(String[] args) {
        const int LIMIT = 5;
        int count = 0;
        boolean isRunning = false;

        do {
            count++;
            if (count >= 2 && !isRunning) {
                isRunning = true;
            }
        } while (count < LIMIT && isRunning);

        System.out.println(count);
        System.out.println(isRunning);
    }
}