"""
Nastran BDF dosyasındaki FORCE kartlarını ayrıştırır ve txt dosyasına yazar.

FORCE kartı formatı (Free-field veya Fixed-field 8 karakter):
FORCE   SID     G       CID     F       N1      N2      N3
"""

import sys
import os
import re
from dataclasses import dataclass
from typing import List


@dataclass
class Force:
    sid: int       # Set ID
    g: int         # Grid point ID
    cid: int       # Coordinate system ID
    f: float       # Scale factor
    n1: float      # X component
    n2: float      # Y component
    n3: float      # Z component


def parse_fixed_field(line: str) -> List[str]:
    """8-karakterlik sabit alan formatını ayrıştırır."""
    fields = []
    # İlk alan 8 karakter (kart adı), sonraki alanlar 8'er karakter
    fields.append(line[0:8].strip())
    for i in range(8, min(len(line), 72), 8):
        fields.append(line[i:i+8].strip())
    return fields


def parse_free_field(line: str) -> List[str]:
    """Virgülle ayrılmış serbest alan formatını ayrıştırır."""
    return [f.strip() for f in line.split(",")]


def to_float(s: str) -> float:
    """Nastran sayı formatını Python float'a çevirir (örn: 1.5+3 -> 1500.0)."""
    s = s.strip()
    if not s:
        return 0.0
    # Nastran kısa bilimsel notasyon: 1.5+3 veya 1.5-3
    s = re.sub(r'([0-9])([+-])([0-9])', r'\1E\2\3', s)
    return float(s)


def parse_bdf(filepath: str) -> List[Force]:
    forces = []

    with open(filepath, "r") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i]

        # Yorum ve boş satırları atla
        stripped = line.strip()
        if not stripped or stripped.startswith("$"):
            i += 1
            continue

        # Satır sonundaki yorum kısmını temizle
        if "$" in line:
            line = line[:line.index("$")]

        # Serbest alan mı (virgül var mı)?
        is_free = "," in line

        if is_free:
            fields = parse_free_field(line)
        else:
            fields = parse_fixed_field(line)

        if not fields:
            i += 1
            continue

        card_name = fields[0].upper().replace("*", "")

        if card_name == "FORCE":
            # Devam satırı kontrolü (8 alan yetmiyorsa)
            all_fields = fields[:]

            # Continuation satırları topla
            while True:
                next_i = i + 1
                if next_i >= len(lines):
                    break
                next_line = lines[next_i].strip()
                if not next_line or next_line.startswith("$"):
                    break
                # Continuation satırı: + veya * ile başlar (sabit), ya da boşlukla
                if next_line.startswith("+") or next_line.startswith("*") or next_line.startswith(" "):
                    cont = lines[next_i]
                    if "$" in cont:
                        cont = cont[:cont.index("$")]
                    if is_free:
                        all_fields += parse_free_field(cont)[1:]
                    else:
                        cont_fields = parse_fixed_field(cont)
                        all_fields += cont_fields[1:]
                    i = next_i
                else:
                    break

            try:
                sid = int(all_fields[1])
                g   = int(all_fields[2])
                cid = int(all_fields[3]) if len(all_fields) > 3 and all_fields[3] else 0
                f_  = to_float(all_fields[4]) if len(all_fields) > 4 and all_fields[4] else 0.0
                n1  = to_float(all_fields[5]) if len(all_fields) > 5 and all_fields[5] else 0.0
                n2  = to_float(all_fields[6]) if len(all_fields) > 6 and all_fields[6] else 0.0
                n3  = to_float(all_fields[7]) if len(all_fields) > 7 and all_fields[7] else 0.0
                forces.append(Force(sid=sid, g=g, cid=cid, f=f_, n1=n1, n2=n2, n3=n3))
            except (IndexError, ValueError) as e:
                print(f"  [UYARI] Satır {i+1} ayrıştırılamadı: {e} -> {all_fields}")

        i += 1

    return forces


def write_forces_to_txt(forces: List[Force], output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        header = (
            f"{'SID':>8}  {'G (Node)':>10}  {'CID':>6}  "
            f"{'F (Scale)':>12}  {'N1 (Fx)':>12}  {'N2 (Fy)':>12}  {'N3 (Fz)':>12}  "
            f"{'Fx_eff':>14}  {'Fy_eff':>14}  {'Fz_eff':>14}\n"
        )
        separator = "-" * len(header.rstrip()) + "\n"

        f.write("=" * len(header.rstrip()) + "\n")
        f.write("  NASTRAN BDF - FORCE KARTLARI\n")
        f.write("=" * len(header.rstrip()) + "\n\n")
        f.write(header)
        f.write(separator)

        for force in forces:
            fx = force.f * force.n1
            fy = force.f * force.n2
            fz = force.f * force.n3
            f.write(
                f"{force.sid:>8}  {force.g:>10}  {force.cid:>6}  "
                f"{force.f:>12.4f}  {force.n1:>12.4f}  {force.n2:>12.4f}  {force.n3:>12.4f}  "
                f"{fx:>14.4f}  {fy:>14.4f}  {fz:>14.4f}\n"
            )

        f.write(separator)
        f.write(f"\nToplam {len(forces)} FORCE kaydı bulundu.\n")


def main():
    if len(sys.argv) < 2:
        print("Kullanım: python parse_bdf_forces.py <input.bdf> [output.txt]")
        print("  output.txt belirtilmezse <input>_forces.txt olarak kaydedilir.")
        sys.exit(1)

    bdf_path = sys.argv[1]
    if not os.path.isfile(bdf_path):
        print(f"Hata: '{bdf_path}' dosyası bulunamadı.")
        sys.exit(1)

    if len(sys.argv) >= 3:
        out_path = sys.argv[2]
    else:
        base = os.path.splitext(bdf_path)[0]
        out_path = base + "_forces.txt"

    print(f"BDF dosyası okunuyor: {bdf_path}")
    forces = parse_bdf(bdf_path)
    print(f"{len(forces)} FORCE kaydı bulundu.")

    write_forces_to_txt(forces, out_path)
    print(f"Sonuçlar yazıldı: {out_path}")


if __name__ == "__main__":
    main()
