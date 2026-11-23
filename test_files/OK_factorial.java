public class Factorial {
    public static int calcFact(int n) {
        if (n <= 1) {
            return 1;
        }
        return n * calcFact(n - 1);
    }

    public static void main(String[] args) {
        int n = 5;
        int result = calcFact(n);
        System.out.println(result);
    }
}