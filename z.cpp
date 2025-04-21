#include <iostream>
#include <vector>

int amount_two(int n){
    while (n%2 == 0){
        n = n/2;
        std::cout << 2 << " ";
    }
    return n;
}

int odd_numbers(int n){
    for (int i = 3; i*i <= n; i+=2){
        while (n%i == 0){
            std::cout << i << " ";
            n = n/i;
        }
    }
    return n;
}

int main(){
    int a;
    std::cin >> a;
    if (a == 1){
        std::cout << a;
    }

    a = amount_two(a);
    a = odd_numbers(a);

    if (a > 2) {
        std::cout << a;
    }
 
    return 0;
}