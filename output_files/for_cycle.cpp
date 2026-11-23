#include <iostream>

using namespace std;

int main()
{
    int sum = 0;
    for (int i = 0; (i < 10); i++)
    {
        if ((i == 3))
        {
            continue;
        }
        if ((i == 7))
        {
            break;
        }
        sum += i;
    }
    (std::cout << std::boolalpha << sum << std::endl);
    return 0;
}
