#include <iostream>
#include <string>
#include <cstdlib>
#include <sstream>
#include <vector>
#include <memory>
#include <initializer_list>
#include <stdexcept>
#include <algorithm>
#include <type_traits>

using namespace std;

template <typename T>
std::string java_to_str(const T &val)
{
    if constexpr (std::is_same_v<T, std::string>)
        return val;
    else if constexpr (std::is_same_v<T, bool>)
        return val ? "true" : "false";
    else if constexpr (std::is_same_v<T, char>)
        return std::string(1, val);
    else
    {
        std::ostringstream oss;
        oss << val;
        return oss.str();
    }
}

inline std::string java_to_str(const char *val)
{
    return std::string(val);
}

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

template <typename T>
class JavaList
{
    std::shared_ptr<std::vector<T>> data;

public:
    JavaList() : data(std::make_shared<std::vector<T>>()) {}

    bool add(const T &item)
    {
        data->push_back(item);
        return true;
    }

    bool isEmpty() const
    {
        return data->empty();
    }

    int size() const
    {
        return static_cast<int>(data->size());
    }

    T &get(int index) const
    {
        return data->at(index);
    }

    bool remove(const T &item)
    {
        auto it = std::find(data->begin(), data->end(), item);
        if (it != data->end())
        {
            data->erase(it);
            return true;
        }
        return false;
    }

    auto begin() { return data->begin(); }
    auto end() { return data->end(); }
    auto begin() const { return data->begin(); }
    auto end() const { return data->end(); }
};

class JavaScanner
{
    std::istream *in;

public:
    JavaScanner() : in(&std::cin) {}
    explicit JavaScanner(std::istream &stream) : in(&stream) {}

    int nextInt()
    {
        int val = 0;
        (*in) >> val;
        return val;
    }

    double nextDouble()
    {
        double val = 0.0;
        (*in) >> val;
        return val;
    }

    std::string nextLine()
    {
        std::string s;
        std::getline(*in, s);
        if (!s.empty() && s.back() == '\r')
            s.pop_back();
        return s;
    }
};

class Task;
class Task
{
private:
    int id;
    string description;
    bool completed;

public:
    Task(int id, string description)
    {
        this->id = id;
        this->description = description;
        this->completed = false;
    }

    int getId()
    {
        return id;
    }

    string getDescription()
    {
        return description;
    }

    bool isCompleted()
    {
        return completed;
    }

    void setCompleted(bool completed)
    {
        this->completed = completed;
    }

    string toString()
    {
        return (java_to_str(id) + java_to_str(". [") + java_to_str((completed ? "X" : " ")) + java_to_str("] ") + java_to_str(description));
    }
};

inline std::ostream &operator<<(std::ostream &os, const std::shared_ptr<Task> &obj)
{
    if (!obj)
        return os << "null";
    return os << obj->toString();
}

// --- Прототипы функций ---
void addTask(JavaScanner scanner);
void listTasks();
void markTaskAsCompleted(JavaScanner scanner);
void removeTask(JavaScanner scanner);

// --- Состояние (переменные) ---
JavaList<std::shared_ptr<Task>> taskList = JavaList<std::shared_ptr<Task>>();
int taskIdCounter = 1;

int main()
{
    JavaScanner scanner = JavaScanner(std::cin);
    while (true)
    {
        (std::cout << std::boolalpha << "To-Do List Application" << std::endl);
        (std::cout << std::boolalpha << "1. Add Task" << std::endl);
        (std::cout << std::boolalpha << "2. List Tasks" << std::endl);
        (std::cout << std::boolalpha << "3. Mark Task as Completed" << std::endl);
        (std::cout << std::boolalpha << "4. Remove Task" << std::endl);
        (std::cout << std::boolalpha << "5. Exit" << std::endl);
        (std::cout << std::boolalpha << "Enter your choice: ");
        int choice = scanner.nextInt();
        scanner.nextLine();
        {
            const auto java_switch_value_0 = choice;
            int java_switch_case_1 = -1;
            if (java_switch_value_0 == 1)
                java_switch_case_1 = 0;
            else if (java_switch_value_0 == 2)
                java_switch_case_1 = 1;
            else if (java_switch_value_0 == 3)
                java_switch_case_1 = 2;
            else if (java_switch_value_0 == 4)
                java_switch_case_1 = 3;
            else if (java_switch_value_0 == 5)
                java_switch_case_1 = 4;
            switch (java_switch_case_1)
            {
            case 0:
                addTask(scanner);
                break;
                ;
            case 1:
                listTasks();
                break;
                ;
            case 2:
                markTaskAsCompleted(scanner);
                break;
                ;
            case 3:
                removeTask(scanner);
                break;
                ;
            case 4:
                (std::cout << std::boolalpha << "Goodbye!" << std::endl);
                std::exit(0);
                ;
            default:
                (std::cout << std::boolalpha << "Invalid choice. Please try again." << std::endl);
                ;
            }
        }
    }
    return 0;
}

void addTask(JavaScanner scanner)
{
    (std::cout << std::boolalpha << "Enter the task description: ");
    string description = scanner.nextLine();
    std::shared_ptr<Task> task = std::make_shared<Task>(taskIdCounter, description);
    taskList.add(task);
    taskIdCounter++;
    (std::cout << std::boolalpha << "Task added successfully!" << std::endl);
}

void listTasks()
{
    if (taskList.isEmpty())
    {
        (std::cout << std::boolalpha << "No tasks to display." << std::endl);
    }
    else
    {
        (std::cout << std::boolalpha << "Tasks:" << std::endl);
        for (std::shared_ptr<Task> task : taskList)
        {
            (std::cout << std::boolalpha << task << std::endl);
        }
    }
}

void markTaskAsCompleted(JavaScanner scanner)
{
    (std::cout << std::boolalpha << "Enter the task ID to mark as completed: ");
    int taskId = scanner.nextInt();
    scanner.nextLine();
    for (std::shared_ptr<Task> task : taskList)
    {
        if ((task->getId() == taskId))
        {
            task->setCompleted(true);
            (std::cout << std::boolalpha << "Task marked as completed." << std::endl);
            return;
        }
    }
    (std::cout << std::boolalpha << "Task not found." << std::endl);
}

void removeTask(JavaScanner scanner)
{
    (std::cout << std::boolalpha << "Enter the task ID to remove: ");
    int taskId = scanner.nextInt();
    scanner.nextLine();
    for (std::shared_ptr<Task> task : taskList)
    {
        if ((task->getId() == taskId))
        {
            taskList.remove(task);
            (std::cout << std::boolalpha << "Task removed." << std::endl);
            return;
        }
    }
    (std::cout << std::boolalpha << "Task not found." << std::endl);
}
