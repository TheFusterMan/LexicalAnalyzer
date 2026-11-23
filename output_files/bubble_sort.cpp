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
    JavaArray<int> a = JavaArray<int>({5, 1, 4, 2, 8});
    for (int i = 0; (i < a.length()); i++)
    {
        for (int j = 0; (j < (a.length() - 1)); j++)
        {
            if ((a[j] > a[(j + 1)]))
            {
                int temp = a[j];
                a[j] = a[(j + 1)];
                a[(j + 1)] = temp;
            }
        }
    }
    for (int i = 0; (i < a.length()); i++)
    {
        (std::cout << std::boolalpha << a[i] << std::endl);
    }
    return 0;
}
