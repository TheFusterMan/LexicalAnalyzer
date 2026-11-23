#include <iostream>

using namespace std;

// --- Прототипы функций ---
int calcFact(int n);

int calcFact(int n)
{
    if ((n <= 1))
    {
        return 1;
    }
    return (n * calcFact((n - 1)));
}

int main()
{
    int n = 5;
    int result = calcFact(n);
    (std::cout << std::boolalpha << result << std::endl);
    return 0;
}
