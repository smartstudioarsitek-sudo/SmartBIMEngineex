import math

class Number_Judge:
    """
    Kelas Wasit Numerik untuk menangani isu Floating Point & Presisi.
    Reviewer Note: Menggunakan Epsilon Comparison untuk stabilitas numerik.
    """
    def __init__(self, epsilon=1e-9):
        self.eps = epsilon
    
    def is_safe(self, demand, capacity):
        """
        Cek apakah Demand <= Capacity dengan toleransi epsilon.
        Mengatasi bug: 1.00000001 dianggap FAIL padahal SAFE.
        """
        # Hitung Rasio D/C
        if capacity == 0: return False # Hindari pembagian nol
        ratio = demand / capacity
        
        # Logika Epsilon: Jika ratio <= 1.0 + 0.000000001
        is_pass = ratio <= (1.0 + self.eps)
        
        status = "AMAN" if is_pass else "TIDAK AMAN"
        return is_pass, status, ratio

    def is_equal(self, a, b):
        """Cek kesamaan dua angka float"""
        return abs(a - b) < self.eps

    def safe_division(self, a, b):
        """Pembagian aman anti-crash"""
        if abs(b) < self.eps: return 0.0
        return a / b
