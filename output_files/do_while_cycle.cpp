#include <iostream>

using namespace std;

int main()
{
    const int LIMIT = 5;
    int count = 0;
    bool isRunning = false;
    do
    {
        count++;
        if (((count >= 2) && (!isRunning)))
        {
            isRunning = true;
        }
    } while (((count < LIMIT) && isRunning));
    (std::cout << std::boolalpha << count << std::endl);
    (std::cout << std::boolalpha << isRunning << std::endl);
    return 0;
}
