public class Features {
    public static void main(String[] args) {
        int[] numbers = {2, 2, 2};
        System.out.println(numbers[0] + numbers[1] * numbers[2]);
        System.out.println((numbers[0] + numbers[1]) * numbers[2]);

        for (int i = 0; i < numbers.length; i++) {
            switch (numbers[i]) {
                case 1:
                case 2:
                    numbers[i]++;
                    break;
                default:
                    numbers[i]--;
            }
        }

        incrementFirst(numbers);
        System.out.println(numbers[0]);

        int[][] matrix = new int[2][3];
        matrix[1][2] = numbers[0];
        System.out.println(matrix[1][2]);

        String command = "done";
        switch (command) {
            case "done":
                System.out.println("OK");
                break;
            default:
                System.out.println("Unknown command");
        }
    }

    static void incrementFirst(int[] values) {
        ++values[0];
    }
}
