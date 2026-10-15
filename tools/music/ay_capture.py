#!/usr/bin/env python3
"""Minimal Z80 emulator to run the Ninja Massacre music engine and capture AY register writes."""

import struct
import sys
from collections import defaultdict


class Z80:
    """Minimal Z80 emulator - just enough to run a Codemasters AY music engine."""

    def __init__(self):
        self.mem = bytearray(65536)
        # Registers (as individual bytes/words)
        self.a = self.f = 0
        self.b = self.c = self.d = self.e = self.h = self.l = 0
        self.a2 = self.f2 = self.b2 = self.c2 = self.d2 = self.e2 = self.h2 = self.l2 = 0
        self.ixh = self.ixl = self.iyh = self.iyl = 0
        self.sp = 0xFFF0
        self.pc = 0
        self.halted = False
        # AY capture
        self.ay_regs = [0] * 16
        self.ay_selected = 0
        self.ay_frames = []  # list of 14-element lists (one per frame)
        self.cycles = 0
        self.max_cycles = 100_000  # safety limit per call

    # Register pair accessors
    @property
    def bc(self): return (self.b << 8) | self.c
    @bc.setter
    def bc(self, v): self.b, self.c = (v >> 8) & 0xFF, v & 0xFF

    @property
    def de(self): return (self.d << 8) | self.e
    @de.setter
    def de(self, v): self.d, self.e = (v >> 8) & 0xFF, v & 0xFF

    @property
    def hl(self): return (self.h << 8) | self.l
    @hl.setter
    def hl(self, v): self.h, self.l = (v >> 8) & 0xFF, v & 0xFF

    @property
    def af(self): return (self.a << 8) | self.f
    @af.setter
    def af(self, v): self.a, self.f = (v >> 8) & 0xFF, v & 0xFF

    @property
    def ix(self): return (self.ixh << 8) | self.ixl
    @ix.setter
    def ix(self, v): self.ixh, self.ixl = (v >> 8) & 0xFF, v & 0xFF

    @property
    def iy(self): return (self.iyl << 8) | self.iyl
    @iy.setter
    def iy(self, v): self.iyh, self.iyl = (v >> 8) & 0xFF, v & 0xFF

    def read8(self, addr):
        return self.mem[addr & 0xFFFF]

    def read16(self, addr):
        return self.mem[addr & 0xFFFF] | (self.mem[(addr + 1) & 0xFFFF] << 8)

    def write8(self, addr, val):
        self.mem[addr & 0xFFFF] = val & 0xFF

    def write16(self, addr, val):
        self.mem[addr & 0xFFFF] = val & 0xFF
        self.mem[(addr + 1) & 0xFFFF] = (val >> 8) & 0xFF

    def push16(self, val):
        self.sp = (self.sp - 2) & 0xFFFF
        self.write16(self.sp, val)

    def pop16(self):
        val = self.read16(self.sp)
        self.sp = (self.sp + 2) & 0xFFFF
        return val

    def fetch8(self):
        val = self.read8(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        return val

    def fetch16(self):
        val = self.read16(self.pc)
        self.pc = (self.pc + 2) & 0xFFFF
        return val

    def signed8(self, v):
        return v - 256 if v > 127 else v

    # Flag helpers
    FLAG_C = 0x01
    FLAG_N = 0x02
    FLAG_PV = 0x04
    FLAG_H = 0x10
    FLAG_Z = 0x40
    FLAG_S = 0x80

    def set_flags_sz(self, val):
        """Set S and Z flags based on 8-bit result."""
        val &= 0xFF
        self.f = (self.f & ~(self.FLAG_S | self.FLAG_Z))
        if val == 0:
            self.f |= self.FLAG_Z
        if val & 0x80:
            self.f |= self.FLAG_S

    def set_flags_logic(self, val):
        """Set flags for AND/OR/XOR."""
        val &= 0xFF
        self.f = 0
        if val == 0:
            self.f |= self.FLAG_Z
        if val & 0x80:
            self.f |= self.FLAG_S
        # Set parity
        p = val
        p ^= p >> 4
        p ^= p >> 2
        p ^= p >> 1
        if not (p & 1):
            self.f |= self.FLAG_PV

    def add8(self, a, b, carry=0):
        result = a + b + carry
        half = (a & 0x0F) + (b & 0x0F) + carry
        self.f = 0
        if (result & 0xFF) == 0:
            self.f |= self.FLAG_Z
        if result & 0x80:
            self.f |= self.FLAG_S
        if result > 0xFF:
            self.f |= self.FLAG_C
        if half > 0x0F:
            self.f |= self.FLAG_H
        if ((a ^ b ^ 0x80) & (a ^ result)) & 0x80:
            self.f |= self.FLAG_PV
        return result & 0xFF

    def sub8(self, a, b, carry=0):
        result = a - b - carry
        half = (a & 0x0F) - (b & 0x0F) - carry
        self.f = self.FLAG_N
        if (result & 0xFF) == 0:
            self.f |= self.FLAG_Z
        if result & 0x80:
            self.f |= self.FLAG_S
        if result < 0:
            self.f |= self.FLAG_C
        if half < 0:
            self.f |= self.FLAG_H
        if ((a ^ b) & (a ^ result)) & 0x80:
            self.f |= self.FLAG_PV
        return result & 0xFF

    def cp8(self, a, b):
        """Compare - same as SUB but don't store result."""
        self.sub8(a, b)

    def inc8(self, val):
        result = (val + 1) & 0xFF
        self.f = (self.f & self.FLAG_C)  # preserve carry
        if result == 0:
            self.f |= self.FLAG_Z
        if result & 0x80:
            self.f |= self.FLAG_S
        if (val & 0x0F) == 0x0F:
            self.f |= self.FLAG_H
        if val == 0x7F:
            self.f |= self.FLAG_PV
        return result

    def dec8(self, val):
        result = (val - 1) & 0xFF
        self.f = (self.f & self.FLAG_C) | self.FLAG_N
        if result == 0:
            self.f |= self.FLAG_Z
        if result & 0x80:
            self.f |= self.FLAG_S
        if (val & 0x0F) == 0x00:
            self.f |= self.FLAG_H
        if val == 0x80:
            self.f |= self.FLAG_PV
        return result

    def add16(self, a, b):
        result = a + b
        self.f = (self.f & (self.FLAG_S | self.FLAG_Z | self.FLAG_PV))
        if result > 0xFFFF:
            self.f |= self.FLAG_C
        if ((a & 0xFFF) + (b & 0xFFF)) > 0xFFF:
            self.f |= self.FLAG_H
        return result & 0xFFFF

    def cond(self, cc):
        """Evaluate condition code."""
        if cc == 0: return not (self.f & self.FLAG_Z)   # NZ
        if cc == 1: return bool(self.f & self.FLAG_Z)    # Z
        if cc == 2: return not (self.f & self.FLAG_C)    # NC
        if cc == 3: return bool(self.f & self.FLAG_C)    # C
        if cc == 4: return not (self.f & self.FLAG_PV)   # PO
        if cc == 5: return bool(self.f & self.FLAG_PV)   # PE
        if cc == 6: return not (self.f & self.FLAG_S)    # P
        if cc == 7: return bool(self.f & self.FLAG_S)    # M
        return False

    def get_reg8(self, idx):
        """Get 8-bit register by index (B=0, C=1, D=2, E=3, H=4, L=5, (HL)=6, A=7)."""
        if idx == 0: return self.b
        if idx == 1: return self.c
        if idx == 2: return self.d
        if idx == 3: return self.e
        if idx == 4: return self.h
        if idx == 5: return self.l
        if idx == 6: return self.read8(self.hl)
        if idx == 7: return self.a
        return 0

    def set_reg8(self, idx, val):
        val &= 0xFF
        if idx == 0: self.b = val
        elif idx == 1: self.c = val
        elif idx == 2: self.d = val
        elif idx == 3: self.e = val
        elif idx == 4: self.h = val
        elif idx == 5: self.l = val
        elif idx == 6: self.write8(self.hl, val)
        elif idx == 7: self.a = val

    def get_rp(self, idx):
        if idx == 0: return self.bc
        if idx == 1: return self.de
        if idx == 2: return self.hl
        if idx == 3: return self.sp
        return 0

    def set_rp(self, idx, val):
        val &= 0xFFFF
        if idx == 0: self.bc = val
        elif idx == 1: self.de = val
        elif idx == 2: self.hl = val
        elif idx == 3: self.sp = val

    def get_rp2(self, idx):
        if idx == 0: return self.bc
        if idx == 1: return self.de
        if idx == 2: return self.hl
        if idx == 3: return self.af
        return 0

    def set_rp2(self, idx, val):
        val &= 0xFFFF
        if idx == 0: self.bc = val
        elif idx == 1: self.de = val
        elif idx == 2: self.hl = val
        elif idx == 3: self.af = val

    def port_out(self, port, val):
        """Handle OUT instruction."""
        # AY register select: port & 0xC002 == 0xC000 (typically 0xFFFD)
        if (port & 0xC002) == 0xC000:
            self.ay_selected = val & 0x0F
        # AY data write: port & 0xC002 == 0x8000 (typically 0xBFFD)
        elif (port & 0xC002) == 0x8000:
            if self.ay_selected < 16:
                self.ay_regs[self.ay_selected] = val & 0xFF

    def port_in(self, port):
        """Handle IN instruction - return 0xFF (no input)."""
        return 0xFF

    def execute_one(self):
        """Execute a single instruction. Returns False to halt."""
        op = self.fetch8()
        self.cycles += 1

        if op == 0x00:  # NOP
            pass
        elif op == 0x76:  # HALT
            self.halted = True
            return False

        # LD r, r' and LD r, n
        elif (op & 0xC0) == 0x40:  # 01 rrr sss - LD r, r'
            dst = (op >> 3) & 7
            src = op & 7
            self.set_reg8(dst, self.get_reg8(src))

        elif (op & 0xC7) == 0x06:  # 00 rrr 110 - LD r, n
            dst = (op >> 3) & 7
            self.set_reg8(dst, self.fetch8())

        # LD rp, nn
        elif (op & 0xCF) == 0x01:  # 00 rr 0001
            rp = (op >> 4) & 3
            self.set_rp(rp, self.fetch16())

        # LD (nn), HL / LD HL, (nn)
        elif op == 0x22:  # LD (nn), HL
            addr = self.fetch16()
            self.write16(addr, self.hl)
        elif op == 0x2A:  # LD HL, (nn)
            addr = self.fetch16()
            self.hl = self.read16(addr)

        # LD (nn), A / LD A, (nn)
        elif op == 0x32:  # LD (nn), A
            addr = self.fetch16()
            self.write8(addr, self.a)
        elif op == 0x3A:  # LD A, (nn)
            addr = self.fetch16()
            self.a = self.read8(addr)

        # LD A, (BC) / LD A, (DE) / LD (BC), A / LD (DE), A
        elif op == 0x0A: self.a = self.read8(self.bc)
        elif op == 0x1A: self.a = self.read8(self.de)
        elif op == 0x02: self.write8(self.bc, self.a)
        elif op == 0x12: self.write8(self.de, self.a)

        # INC/DEC rp
        elif (op & 0xCF) == 0x03:  # INC rp
            rp = (op >> 4) & 3
            self.set_rp(rp, (self.get_rp(rp) + 1) & 0xFFFF)
        elif (op & 0xCF) == 0x0B:  # DEC rp
            rp = (op >> 4) & 3
            self.set_rp(rp, (self.get_rp(rp) - 1) & 0xFFFF)

        # INC/DEC r
        elif (op & 0xC7) == 0x04:  # INC r
            r = (op >> 3) & 7
            self.set_reg8(r, self.inc8(self.get_reg8(r)))
        elif (op & 0xC7) == 0x05:  # DEC r
            r = (op >> 3) & 7
            self.set_reg8(r, self.dec8(self.get_reg8(r)))

        # ADD HL, rp
        elif (op & 0xCF) == 0x09:
            rp = (op >> 4) & 3
            self.hl = self.add16(self.hl, self.get_rp(rp))

        # ALU A, r and ALU A, n
        elif (op & 0xC0) == 0x80:  # ALU A, r
            alu = (op >> 3) & 7
            val = self.get_reg8(op & 7)
            self._alu(alu, val)
        elif (op & 0xC7) == 0xC6:  # ALU A, n
            alu = (op >> 3) & 7
            val = self.fetch8()
            self._alu(alu, val)

        # PUSH/POP
        elif (op & 0xCF) == 0xC5:  # PUSH rp2
            rp = (op >> 4) & 3
            self.push16(self.get_rp2(rp))
        elif (op & 0xCF) == 0xC1:  # POP rp2
            rp = (op >> 4) & 3
            self.set_rp2(rp, self.pop16())

        # JP nn / JP cc, nn
        elif op == 0xC3:
            self.pc = self.fetch16()
        elif (op & 0xC7) == 0xC2:
            addr = self.fetch16()
            if self.cond((op >> 3) & 7):
                self.pc = addr

        # JR e / JR cc, e
        elif op == 0x18:
            offset = self.signed8(self.fetch8())
            self.pc = (self.pc + offset) & 0xFFFF
        elif op in (0x20, 0x28, 0x30, 0x38):
            offset = self.signed8(self.fetch8())
            cc = {0x20: 0, 0x28: 1, 0x30: 2, 0x38: 3}[op]
            if self.cond(cc):
                self.pc = (self.pc + offset) & 0xFFFF

        # CALL nn / CALL cc, nn
        elif op == 0xCD:
            addr = self.fetch16()
            self.push16(self.pc)
            self.pc = addr
        elif (op & 0xC7) == 0xC4:
            addr = self.fetch16()
            if self.cond((op >> 3) & 7):
                self.push16(self.pc)
                self.pc = addr

        # RET / RET cc
        elif op == 0xC9:
            self.pc = self.pop16()
        elif (op & 0xC7) == 0xC0:
            if self.cond((op >> 3) & 7):
                self.pc = self.pop16()

        # RST
        elif (op & 0xC7) == 0xC7:
            self.push16(self.pc)
            self.pc = op & 0x38

        # JP (HL)
        elif op == 0xE9:
            self.pc = self.hl

        # EX DE, HL
        elif op == 0xEB:
            self.de, self.hl = self.hl, self.de

        # EX AF, AF'
        elif op == 0x08:
            self.a, self.a2 = self.a2, self.a
            self.f, self.f2 = self.f2, self.f

        # EXX
        elif op == 0xD9:
            self.b, self.b2 = self.b2, self.b
            self.c, self.c2 = self.c2, self.c
            self.d, self.d2 = self.d2, self.d
            self.e, self.e2 = self.e2, self.e
            self.h, self.h2 = self.h2, self.h
            self.l, self.l2 = self.l2, self.l

        # RLCA, RRCA, RLA, RRA
        elif op == 0x07:  # RLCA
            c = (self.a >> 7) & 1
            self.a = ((self.a << 1) | c) & 0xFF
            self.f = (self.f & (self.FLAG_S | self.FLAG_Z | self.FLAG_PV)) | c
        elif op == 0x0F:  # RRCA
            c = self.a & 1
            self.a = ((self.a >> 1) | (c << 7)) & 0xFF
            self.f = (self.f & (self.FLAG_S | self.FLAG_Z | self.FLAG_PV)) | c
        elif op == 0x17:  # RLA
            c = (self.a >> 7) & 1
            self.a = ((self.a << 1) | (self.f & self.FLAG_C)) & 0xFF
            self.f = (self.f & (self.FLAG_S | self.FLAG_Z | self.FLAG_PV)) | c
        elif op == 0x1F:  # RRA
            c = self.a & 1
            self.a = ((self.a >> 1) | ((self.f & self.FLAG_C) << 7)) & 0xFF
            self.f = (self.f & (self.FLAG_S | self.FLAG_Z | self.FLAG_PV)) | c

        # DI / EI (ignore for music engine)
        elif op == 0xF3 or op == 0xFB:
            pass

        # OUT (n), A
        elif op == 0xD3:
            port = self.fetch8() | (self.a << 8)
            self.port_out(port, self.a)

        # IN A, (n)
        elif op == 0xDB:
            port = self.fetch8() | (self.a << 8)
            self.a = self.port_in(port)

        # SCF / CCF
        elif op == 0x37:  # SCF
            self.f = (self.f & (self.FLAG_S | self.FLAG_Z | self.FLAG_PV)) | self.FLAG_C
        elif op == 0x3F:  # CCF
            c = self.f & self.FLAG_C
            self.f = (self.f & (self.FLAG_S | self.FLAG_Z | self.FLAG_PV)) | (self.FLAG_H if c else 0) | (0 if c else self.FLAG_C)

        # CPL
        elif op == 0x2F:
            self.a = self.a ^ 0xFF
            self.f |= (self.FLAG_H | self.FLAG_N)

        # DJNZ
        elif op == 0x10:
            offset = self.signed8(self.fetch8())
            self.b = (self.b - 1) & 0xFF
            if self.b != 0:
                self.pc = (self.pc + offset) & 0xFFFF

        # LD SP, HL
        elif op == 0xF9:
            self.sp = self.hl

        # CB prefix (bit operations)
        elif op == 0xCB:
            self._exec_cb()

        # ED prefix
        elif op == 0xED:
            self._exec_ed()

        # DD prefix (IX)
        elif op == 0xDD:
            self._exec_ddfd('ix')

        # FD prefix (IY)
        elif op == 0xFD:
            self._exec_ddfd('iy')

        else:
            print(f"Unknown opcode: {op:02x} at PC={self.pc-1:04x}")
            return False

        return True

    def _alu(self, op, val):
        if op == 0: self.a = self.add8(self.a, val)          # ADD
        elif op == 1: self.a = self.add8(self.a, val, self.f & 1)  # ADC
        elif op == 2: self.a = self.sub8(self.a, val)          # SUB
        elif op == 3: self.a = self.sub8(self.a, val, self.f & 1)  # SBC
        elif op == 4:  # AND
            self.a &= val
            self.set_flags_logic(self.a)
            self.f |= self.FLAG_H
        elif op == 5:  # XOR
            self.a ^= val
            self.set_flags_logic(self.a)
        elif op == 6:  # OR
            self.a |= val
            self.set_flags_logic(self.a)
        elif op == 7:  # CP
            self.sub8(self.a, val)

    def _exec_cb(self):
        op = self.fetch8()
        r = op & 7
        val = self.get_reg8(r)
        bit_op = (op >> 6) & 3
        bit_n = (op >> 3) & 7

        if bit_op == 0:  # Rotates/shifts
            result = self._shift(bit_n, val)
            self.set_reg8(r, result)
        elif bit_op == 1:  # BIT
            test = val & (1 << bit_n)
            self.f = (self.f & self.FLAG_C) | self.FLAG_H
            if not test:
                self.f |= self.FLAG_Z
            if bit_n == 7 and test:
                self.f |= self.FLAG_S
        elif bit_op == 2:  # RES
            self.set_reg8(r, val & ~(1 << bit_n))
        elif bit_op == 3:  # SET
            self.set_reg8(r, val | (1 << bit_n))

    def _shift(self, op, val):
        if op == 0:  # RLC
            c = (val >> 7) & 1
            result = ((val << 1) | c) & 0xFF
        elif op == 1:  # RRC
            c = val & 1
            result = ((val >> 1) | (c << 7)) & 0xFF
        elif op == 2:  # RL
            c = (val >> 7) & 1
            result = ((val << 1) | (self.f & self.FLAG_C)) & 0xFF
        elif op == 3:  # RR
            c = val & 1
            result = ((val >> 1) | ((self.f & self.FLAG_C) << 7)) & 0xFF
        elif op == 4:  # SLA
            c = (val >> 7) & 1
            result = (val << 1) & 0xFF
        elif op == 5:  # SRA
            c = val & 1
            result = ((val >> 1) | (val & 0x80)) & 0xFF
        elif op == 6:  # SLL (undocumented, SLA but sets bit 0)
            c = (val >> 7) & 1
            result = ((val << 1) | 1) & 0xFF
        elif op == 7:  # SRL
            c = val & 1
            result = (val >> 1) & 0xFF
        else:
            c = 0
            result = val

        self.f = c
        if result == 0: self.f |= self.FLAG_Z
        if result & 0x80: self.f |= self.FLAG_S
        # Parity
        p = result
        p ^= p >> 4; p ^= p >> 2; p ^= p >> 1
        if not (p & 1): self.f |= self.FLAG_PV
        return result

    def _exec_ed(self):
        op = self.fetch8()

        if op == 0x47:  # LD I, A
            pass  # ignore
        elif op == 0x4F:  # LD R, A
            pass  # ignore
        elif op == 0x57:  # LD A, I
            self.a = 0; self.set_flags_sz(self.a)
        elif op == 0x5F:  # LD A, R
            self.a = 0; self.set_flags_sz(self.a)

        # LD (nn), rp / LD rp, (nn)
        elif (op & 0xCF) == 0x43:  # LD (nn), rp
            addr = self.fetch16()
            rp = (op >> 4) & 3
            self.write16(addr, self.get_rp(rp))
        elif (op & 0xCF) == 0x4B:  # LD rp, (nn)
            addr = self.fetch16()
            rp = (op >> 4) & 3
            self.set_rp(rp, self.read16(addr))

        # OUT (C), r / IN r, (C)
        elif (op & 0xC7) == 0x41:  # OUT (C), r
            r = (op >> 3) & 7
            self.port_out(self.bc, self.get_reg8(r))
        elif (op & 0xC7) == 0x40:  # IN r, (C)
            r = (op >> 3) & 7
            val = self.port_in(self.bc)
            if r != 6:
                self.set_reg8(r, val)
            self.set_flags_logic(val)

        # Block I/O
        elif op == 0xA3:  # OUTI
            val = self.read8(self.hl)
            self.port_out(self.bc, val)
            self.hl = (self.hl + 1) & 0xFFFF
            self.b = (self.b - 1) & 0xFF
            self.f = self.FLAG_N
            if self.b == 0: self.f |= self.FLAG_Z
        elif op == 0xAB:  # OUTD
            val = self.read8(self.hl)
            self.port_out(self.bc, val)
            self.hl = (self.hl - 1) & 0xFFFF
            self.b = (self.b - 1) & 0xFF
            self.f = self.FLAG_N
            if self.b == 0: self.f |= self.FLAG_Z

        # LDIR / LDDR / LDI / LDD
        elif op == 0xB0:  # LDIR
            while True:
                self.write8(self.de, self.read8(self.hl))
                self.hl = (self.hl + 1) & 0xFFFF
                self.de = (self.de + 1) & 0xFFFF
                self.bc = (self.bc - 1) & 0xFFFF
                if self.bc == 0:
                    break
            self.f &= ~(self.FLAG_H | self.FLAG_PV | self.FLAG_N)
        elif op == 0xA0:  # LDI
            self.write8(self.de, self.read8(self.hl))
            self.hl = (self.hl + 1) & 0xFFFF
            self.de = (self.de + 1) & 0xFFFF
            self.bc = (self.bc - 1) & 0xFFFF
            self.f &= ~(self.FLAG_H | self.FLAG_N)
            if self.bc: self.f |= self.FLAG_PV
            else: self.f &= ~self.FLAG_PV

        # NEG
        elif op == 0x44:
            old_a = self.a
            self.a = self.sub8(0, old_a)

        # SBC HL, rp
        elif (op & 0xCF) == 0x42:
            rp = (op >> 4) & 3
            val = self.get_rp(rp)
            c = self.f & self.FLAG_C
            result = self.hl - val - c
            self.f = self.FLAG_N
            if (result & 0xFFFF) == 0: self.f |= self.FLAG_Z
            if result & 0x8000: self.f |= self.FLAG_S
            if result < 0: self.f |= self.FLAG_C
            self.hl = result & 0xFFFF

        # ADC HL, rp
        elif (op & 0xCF) == 0x4A:
            rp = (op >> 4) & 3
            val = self.get_rp(rp)
            c = self.f & self.FLAG_C
            result = self.hl + val + c
            self.f = 0
            if (result & 0xFFFF) == 0: self.f |= self.FLAG_Z
            if result & 0x8000: self.f |= self.FLAG_S
            if result > 0xFFFF: self.f |= self.FLAG_C
            self.hl = result & 0xFFFF

        # RETI / RETN
        elif op in (0x4D, 0x45):
            self.pc = self.pop16()

        else:
            print(f"Unknown ED opcode: ED {op:02x} at PC={self.pc-2:04x}")

    def _exec_ddfd(self, reg):
        """Execute DD/FD prefixed instruction (IX/IY)."""
        op = self.fetch8()

        def get_idx():
            return self.ix if reg == 'ix' else self.iy
        def set_idx(v):
            if reg == 'ix': self.ix = v & 0xFFFF
            else: self.iy = v & 0xFFFF
        def get_idxh():
            return self.ixh if reg == 'ix' else self.iyh
        def set_idxh(v):
            if reg == 'ix': self.ixh = v & 0xFF
            else: self.iyh = v & 0xFF
        def get_idxl():
            return self.ixl if reg == 'ix' else self.iyl
        def set_idxl(v):
            if reg == 'ix': self.ixl = v & 0xFF
            else: self.iyl = v & 0xFF

        if op == 0x21:  # LD IX, nn
            set_idx(self.fetch16())
        elif op == 0x22:  # LD (nn), IX
            addr = self.fetch16()
            self.write16(addr, get_idx())
        elif op == 0x2A:  # LD IX, (nn)
            addr = self.fetch16()
            set_idx(self.read16(addr))
        elif op == 0x36:  # LD (IX+d), n
            d = self.signed8(self.fetch8())
            n = self.fetch8()
            self.write8((get_idx() + d) & 0xFFFF, n)
        elif op == 0xF9:  # LD SP, IX
            self.sp = get_idx()
        elif op == 0xE5:  # PUSH IX
            self.push16(get_idx())
        elif op == 0xE1:  # POP IX
            set_idx(self.pop16())
        elif op == 0xE9:  # JP (IX)
            self.pc = get_idx()
        elif op == 0x23:  # INC IX
            set_idx(get_idx() + 1)
        elif op == 0x2B:  # DEC IX
            set_idx(get_idx() - 1)
        elif op == 0xE3:  # EX (SP), IX
            val = self.read16(self.sp)
            self.write16(self.sp, get_idx())
            set_idx(val)

        # ADD IX, rp (note: rp=2 means IX itself)
        elif (op & 0xCF) == 0x09:
            rp = (op >> 4) & 3
            if rp == 2:
                val = get_idx()
            else:
                val = self.get_rp(rp)
            set_idx(self.add16(get_idx(), val))

        # LD r, (IX+d) / LD (IX+d), r
        elif (op & 0xC7) == 0x46 and op != 0x76:  # LD r, (IX+d)
            d = self.signed8(self.fetch8())
            dst = (op >> 3) & 7
            self.set_reg8(dst, self.read8((get_idx() + d) & 0xFFFF))
        elif (op & 0xF8) == 0x70 and op != 0x76:  # LD (IX+d), r
            d = self.signed8(self.fetch8())
            src = op & 7
            self.write8((get_idx() + d) & 0xFFFF, self.get_reg8(src))

        # INC/DEC (IX+d)
        elif op == 0x34:  # INC (IX+d)
            d = self.signed8(self.fetch8())
            addr = (get_idx() + d) & 0xFFFF
            self.write8(addr, self.inc8(self.read8(addr)))
        elif op == 0x35:  # DEC (IX+d)
            d = self.signed8(self.fetch8())
            addr = (get_idx() + d) & 0xFFFF
            self.write8(addr, self.dec8(self.read8(addr)))

        # ALU A, (IX+d)
        elif (op & 0xC7) == 0x86:  # ADD/ADC/SUB/SBC/AND/XOR/OR/CP A, (IX+d)
            d = self.signed8(self.fetch8())
            val = self.read8((get_idx() + d) & 0xFFFF)
            alu = (op >> 3) & 7
            self._alu(alu, val)

        # DD CB d op - bit operations on (IX+d)
        elif op == 0xCB:
            d = self.signed8(self.fetch8())
            cb_op = self.fetch8()
            addr = (get_idx() + d) & 0xFFFF
            val = self.read8(addr)
            bit_op = (cb_op >> 6) & 3
            bit_n = (cb_op >> 3) & 7
            if bit_op == 0:  # Shift/rotate
                result = self._shift(bit_n, val)
                self.write8(addr, result)
            elif bit_op == 1:  # BIT
                test = val & (1 << bit_n)
                self.f = (self.f & self.FLAG_C) | self.FLAG_H
                if not test: self.f |= self.FLAG_Z
                if bit_n == 7 and test: self.f |= self.FLAG_S
            elif bit_op == 2:  # RES
                self.write8(addr, val & ~(1 << bit_n))
            elif bit_op == 3:  # SET
                self.write8(addr, val | (1 << bit_n))

        # Undocumented: LD IXH/IXL, n etc.
        elif op == 0x26:  # LD IXH, n
            set_idxh(self.fetch8())
        elif op == 0x2E:  # LD IXL, n
            set_idxl(self.fetch8())

        else:
            print(f"Unknown {'DD' if reg == 'ix' else 'FD'} opcode: {0xDD if reg == 'ix' else 0xFD:02x} {op:02x} at PC={self.pc-2:04x}")

    def call(self, addr):
        """Call a subroutine and run until it returns to our sentinel."""
        sentinel = 0xFFFC  # unused address as return marker
        self.push16(sentinel)
        self.pc = addr
        self.cycles = 0
        while self.pc != sentinel and self.cycles < self.max_cycles:
            if not self.execute_one():
                break
        if self.cycles >= self.max_cycles:
            print(f"WARNING: Max cycles reached at PC={self.pc:04x}")


def load_page(cpu, page_data, base_addr):
    """Load a memory page into the CPU's address space."""
    for i, b in enumerate(page_data):
        cpu.mem[(base_addr + i) & 0xFFFF] = b


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract AY music from Ninja Massacre")
    parser.add_argument("--song", type=int, default=0, help="Song number (0-6)")
    parser.add_argument("--frames", type=int, default=3000, help="Number of frames to capture (50fps)")
    parser.add_argument("--output", default="music.psg", help="Output PSG file")
    parser.add_argument("--txt", action="store_true", help="Also output human-readable text")
    args = parser.parse_args()

    cpu = Z80()

    # Load bank 1 (page 4) at 0xC000 - this is where the music engine lives
    with open("page_4.bin", "rb") as f:
        load_page(cpu, f.read(), 0xC000)

    # The music engine also reads from its own RAM area (0xC000-0xFFFF)
    # But we also need the area visible at other addresses if the engine references them
    # For now, bank 1 at C000 should be sufficient

    print(f"Initializing song {args.song}...")
    cpu.a = args.song
    cpu.call(0xC000)  # JP 0xC00E (init)

    print(f"Capturing {args.frames} frames ({args.frames/50:.1f} seconds)...")

    frames = []
    for frame in range(args.frames):
        cpu.call(0xC003)  # JP 0xC0CD (tick)
        frames.append(list(cpu.ay_regs[:14]))

    # Write PSG file format
    # PSG format: header "PSG\x1A", then frames of AY register writes
    # Each frame: register_number, value pairs, terminated by 0xFF
    # 0xFE = frame end (wait one interrupt)
    with open(args.output, "wb") as f:
        f.write(b"PSG\x1a")  # Magic
        f.write(bytes([0] * 12))  # Header padding (version, etc.)

        prev_regs = [0] * 14
        for frame_data in frames:
            # Write changed registers
            for reg in range(14):
                if frame_data[reg] != prev_regs[reg]:
                    f.write(bytes([reg, frame_data[reg]]))
            f.write(bytes([0xFF]))  # End of frame marker
            prev_regs = list(frame_data)

    print(f"Wrote {args.output} ({len(frames)} frames)")

    if args.txt:
        txt_file = args.output.rsplit(".", 1)[0] + ".txt"
        with open(txt_file, "w") as f:
            f.write("Frame  ToneA   ToneB   ToneC   Noise Mix   VolA VolB VolC EnvPer  EnvShp\n")
            f.write("-" * 80 + "\n")
            for i, fr in enumerate(frames):
                tone_a = fr[0] | ((fr[1] & 0x0F) << 8)
                tone_b = fr[2] | ((fr[3] & 0x0F) << 8)
                tone_c = fr[4] | ((fr[5] & 0x0F) << 8)
                noise = fr[6] & 0x1F
                mixer = fr[7]
                vol_a = fr[8] & 0x1F
                vol_b = fr[9] & 0x1F
                vol_c = fr[10] & 0x1F
                env_per = fr[11] | (fr[12] << 8)
                env_shp = fr[13]
                f.write(f"{i:5d}  {tone_a:5d}   {tone_b:5d}   {tone_c:5d}   {noise:3d}  {mixer:02x}  "
                        f" {vol_a:3d}  {vol_b:3d}  {vol_c:3d}  {env_per:5d}   {env_shp:3d}\n")
        print(f"Wrote {txt_file}")

    # Also dump as raw register frames for easy processing
    raw_file = args.output.rsplit(".", 1)[0] + ".raw"
    with open(raw_file, "wb") as f:
        for frame_data in frames:
            f.write(bytes(frame_data))
    print(f"Wrote {raw_file} (14 bytes per frame)")


if __name__ == "__main__":
    main()
