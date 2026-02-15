import math

class Number_Judge:
    def __init__(self, epsilon=1e-9):
        self.eps = epsilon
    
    def is_safe(self, value, limit):
        """
        Cek apakah value <= limit dengan toleransi.
        Mengatasi bug 0.300000000004 > 0.3
        """
        # Jika selisihnya sangat kecil, anggap sama
        if abs(value - limit) < self.eps:
            return True
        return value < limit

    def is_equal(self, a, b):
        return abs(a - b) < self.eps

    def cek_status(self, rasio_capacity):
        """Helper untuk status keamanan struktur"""
        # Rasio <= 1.0 dianggap AMAN (dengan toleransi)
        if rasio_capacity <= (1.0 + self.eps):
            return "AMAN"
        else:
            return "TIDAK AMAN (OVER)"
