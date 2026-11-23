#include <iostream>
#include <vector>
#include <memory>
#include <initializer_list>
#include <stdexcept>
#include <type_traits>

using namespace std;

struct JavaArraySizes
{
    std::vector<int> values;

    JavaArraySizes(std::initializer_list<int> sizes) : values(sizes)
    {
        for (int size : values)
        {
            if (size < 0)
                throw std::length_error("Negative array size");
        }
    }
};

template <typename T>
class JavaArray;
template <typename T>
struct IsJavaArray : std::false_type
{
};
template <typename T>
struct IsJavaArray<JavaArray<T>> : std::true_type
{
};

template <typename T>
class JavaArray
{
    std::shared_ptr<std::vector<T>> data;

    void check_data() const
    {
        if (!data)
            throw std::runtime_error("Null array reference");
    }

public:
    JavaArray() = default;

    explicit JavaArray(int size)
    {
        if (size < 0)
            throw std::length_error("Negative array size");
        data = std::make_shared<std::vector<T>>(size);
    }

    JavaArray(std::initializer_list<T> values)
        : data(std::make_shared<std::vector<T>>(values)) {}

    explicit JavaArray(const JavaArraySizes &sizes, std::size_t dimension = 0)
        : JavaArray(sizes.values.at(dimension))
    {
        if constexpr (IsJavaArray<T>::value)
        {
            if (dimension + 1 < sizes.values.size())
            {
                for (auto &item : *data)
                    item = T(sizes, dimension + 1);
            }
        }
    }

    int length() const
    {
        check_data();
        return static_cast<int>(data->size());
    }

    typename std::vector<T>::reference operator[](int index) const
    {
        check_data();
        return data->at(index);
    }

    bool operator==(const JavaArray &other) const { return data == other.data; }
    bool operator!=(const JavaArray &other) const { return data != other.data; }
};

int main()
{
    JavaArray<char> alphabet = JavaArray<char>({'a', 'b', 'c', 'd', 'e', '1', '2', '3', '4'});
    int length = 5;
    int alphabetLength = alphabet.length();
    int max = (alphabetLength - 1);
    int min = 0;
    int range = ((max - min) + 1);
    int seed = 7;
    for (int i = 0; (i < length); i++)
    {
        seed = (((seed * 31) + 17) % range);
        int index = (seed + min);
        if ((index < 0))
        {
            index = (-index);
        }
        index = (index % alphabetLength);
        (std::cout << std::boolalpha << alphabet[index] << std::endl);
    }
    return 0;
}
