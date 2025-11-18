let arr = [1,3,51,76,182, 7];

for (let i = 0; i < 6; i = i +1){
    print(arr[i]);
    print(", ");
}

print("\nAfter:\n");
for (let j = 0; j < 6; j = j +1){
    arr[j] = j;
}

for (let k = 0; k < 6; k = k +1){
    print(arr[k]);
    print(", ");
}