public class BitwiseOps {
    public static void main(String[] args) {
        int a = 12;
        int b = 25;
        System.out.println(a & b);
        System.out.println(a | b);
        System.out.println(a ^ b);

        int neg = -8;
        int shifted = neg >>> 1;
        System.out.println(shifted);
    }
}