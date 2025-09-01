let tem : integer[][][];

// Expected: int[][] received int
tem[1] = 1; // Expected: int[][] received int

// Expected int[] received int[][]
tem[1][1] = [[1,2], [3,4]];

// Expected int received int[]
tem[1][3][4] = [1];

