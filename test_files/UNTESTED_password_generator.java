public class PasswordGenerator {
    public static void main(String[] args) {
        char[] alphabet = {'a', 'b', 'c', 'd', 'e', '1', '2', '3', '4'};
        int length = 5;
        int alphabetLength = alphabet.length;
        int max = alphabetLength - 1;
        int min = 0;
        int range = max - min + 1;

        int seed = 7;
        for (int i = 0; i < length; i++) {
            seed = (seed * 31 + 17) % range;
            int index = seed + min;
            if (index < 0) {
                index = -index;
            }
            index = index % alphabetLength;
            System.out.println(alphabet[index]);
        }
    }
}