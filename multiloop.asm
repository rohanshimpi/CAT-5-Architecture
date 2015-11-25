; sum an array
       go   0
0      ld   2 .count
	   ldi  4 3     ; r2 has value of counter
       ldi  3 .count2     ; r3 points to first value
       ldi  1 0       ; r1 contains sum
.loop1 ldi  3 .count2
       dec  4
	   ld   2 .count
.loop  add  1 *3      ; r1 = r1 + next array value
       inc  3
       dec  2
       bnz  2 .loop
       bnz  4 .loop1
       st	1 75
       sys  1 50
       dw   0 
.count dw   5
.count2  dw   3
       dw   2
       dw   0
       dw   8
       dw   100
50     dw   0
       end
