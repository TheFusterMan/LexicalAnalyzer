from analizer import Analizer

if __name__ == "__main__":
    analizer = Analizer()
    code_to_tokenize = """
    public class Main {
        public static void main(String[] args) {
            int x = 10;
            while (x > 0) {
                int y = x * 2;
                x = x - 1;
            }
            System.out.println("Готово");
        }
    }
    """

    for token in analizer.tokenize(code_to_tokenize):
        print(token)