public class CommandParser {
    public static void main(String[] args) {
        String cmd = "start";
        switch (cmd) {
            case "init":
                System.out.println(1);
                break;
            case "start":
            case "run":
                System.out.println(2);
                break;
            case "stop":
                System.out.println(3);
                break;
            default:
                System.out.println(0);
        }
    }
}