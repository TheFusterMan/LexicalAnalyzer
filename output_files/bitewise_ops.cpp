#include <iostream>
#include <type_traits>
#include <climits>

using namespace std;

template <typename T, typename U>
auto java_unsigned_shift(T value, U count) -> decltype(+value)
{
    using Result = decltype(+value);
    using Unsigned = typename std::make_unsigned<Result>::type;
    constexpr unsigned int mask = sizeof(Result) * CHAR_BIT - 1;
    return static_cast<Result>(static_cast<Unsigned>(value) >> (count & mask));
}

template <typename T, typename U>
T &java_unsigned_shift_assign(T &value, U count)
{
    value = static_cast<T>(java_unsigned_shift(value, count));
    return value;
}

int main()
{
    int a = 12;
    int b = 25;
    (std::cout << std::boolalpha << (a & b) << std::endl);
    (std::cout << std::boolalpha << (a | b) << std::endl);
    (std::cout << std::boolalpha << (a ^ b) << std::endl);
    int neg = (-8);
    int shifted = java_unsigned_shift(neg, 1);
    (std::cout << std::boolalpha << shifted << std::endl);
    return 0;
}
