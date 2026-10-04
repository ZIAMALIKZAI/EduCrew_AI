import io
import zipfile
import hmac
import hashlib
import os
import pandas as pd
from PIL import Image, ImageDraw
import qrcode

HMAC_SECRET = os.getenv("EDUCREW_SIGNING_SECRET", "educrew_pk_gov_sec_2026").encode()

class IDCardService:
    @classmethod
    def sign_payload(cls, raw_data: str) -> str:
        """Generates HMAC-SHA256 signature for Pakistani Institutional Cards."""
        clean_data = str(raw_data) if raw_data is not None else ""
        return hmac.new(HMAC_SECRET, clean_data.encode("utf-8"), hashlib.sha256).hexdigest()[:12]

    @staticmethod
    def _clean_str(val, default=""):
        """Safely converts any Pandas cell (NaN, float, int, None) to a clean string."""
        if val is None or pd.isna(val):
            return default
        s = str(val).strip()
        # Remove trailing .0 if an integer was parsed as float (e.g. roll number 12.0)
        if s.endswith(".0"):
            s = s[:-2]
        return s if s else default

    # ---------------- 1. STUDENT OFFICIAL CARD ----------------
    @classmethod
    def create_student_card(
        cls,
        admission_no: str,
        roll_no: str,
        student_name: str,
        father_name: str,
        class_name: str,
        section: str = "A",
        blood_group: str = "B+",
        emergency_contact: str = "+92 300 0000000",
        school_name: str = "GOVERNMENT HIGH SCHOOL",
        school_phone: str = "+92 91 1234567",
        school_email: str = "info@school.edu.pk"
    ) -> Image.Image:
        admission_no = cls._clean_str(admission_no, "ADM-NEW")
        roll_no = cls._clean_str(roll_no, "1")
        student_name = cls._clean_str(student_name, "STUDENT")
        father_name = cls._clean_str(father_name, "GUARDIAN")
        class_name = cls._clean_str(class_name, "Class 10th")
        section = cls._clean_str(section, "A")
        blood_group = cls._clean_str(blood_group, "O+")
        emergency_contact = cls._clean_str(emergency_contact, "N/A")
        school_name = cls._clean_str(school_name, "GOVERNMENT SCHOOL")
        school_phone = cls._clean_str(school_phone, "+92 000 0000000")
        school_email = cls._clean_str(school_email, "info@school.edu.pk")

        width, height = 600, 980
        card = Image.new("RGB", (width, height), "#FFFFFF")
        draw = ImageDraw.Draw(card)

        # Header - Emerald Green
        draw.rectangle([(0, 0), (width, 150)], fill="#065F46")
        draw.rectangle([(0, 150), (width, 160)], fill="#F59E0B")

        draw.text((width // 2, 45), school_name.upper(), fill="#FFFFFF", anchor="mm")
        draw.text((width // 2, 85), "STUDENT IDENTITY CARD", fill="#D1FAE5", anchor="mm")
        draw.text((width // 2, 120), "ACADEMIC SESSION: 2026 - 2027", fill="#FDE68A", anchor="mm")

        # Avatar placeholder
        center_x = width // 2
        avatar_y = 250
        radius = 70
        draw.ellipse([(center_x - radius - 4, avatar_y - radius - 4), (center_x + radius + 4, avatar_y + radius + 4)], fill="#F59E0B")
        draw.ellipse([(center_x - radius, avatar_y - radius), (center_x + radius, avatar_y + radius)], fill="#E2E8F0")
        draw.ellipse([(center_x - 28, avatar_y - 40), (center_x + 28, avatar_y + 10)], fill="#94A3B8")
        draw.chord([(center_x - 50, avatar_y - 5), (center_x + 50, avatar_y + 65)], 0, 180, fill="#94A3B8")

        # Class Pill Badge
        badge_text = f"STUDENT • {class_name.upper()} ({section.upper()})"
        draw.rounded_rectangle([(center_x - 170, 345), (center_x + 170, 380)], radius=17, fill="#065F46")
        draw.text((center_x, 362), badge_text, fill="#FFFFFF", anchor="mm")

        # Student Name
        draw.text((center_x, 415), student_name.upper(), fill="#0F172A", anchor="mm")

        # Data Box
        box_top = 450
        draw.rounded_rectangle([(35, box_top), (width - 35, box_top + 185)], radius=12, fill="#F8FAFC", outline="#E2E8F0", width=2)

        fields = [
            ("Father's Name :", father_name.title()),
            ("Admission No   :", admission_no),
            ("Class Roll No  :", roll_no),
            ("Blood Group    :", blood_group),
            ("Emergency Call :", emergency_contact)
        ]

        y_offset = box_top + 22
        for label, val in fields:
            draw.text((55, y_offset), label, fill="#64748B")
            val_color = "#DC2626" if "Blood" in label else "#0F172A"
            draw.text((220, y_offset), str(val), fill=val_color)
            y_offset += 32

        # Signed QR Code
        raw_body = f"STU|{admission_no}|{student_name}|{class_name}|{roll_no}|{emergency_contact}"
        sig = cls.sign_payload(raw_body)
        signed_token = f"{raw_body}#{sig}"

        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=2)
        qr.add_data(signed_token)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#065F46", back_color="white").convert("RGB").resize((150, 150))
        card.paste(qr_img, (center_x - 75, 660))

        draw.text((center_x, 825), "SCAN AT CAMPUS GATE FOR DAILY ATTENDANCE", fill="#64748B", anchor="mm")

        # Footer
        draw.rectangle([(0, 860), (width, height)], fill="#0F172A")
        draw.text((center_x, 888), f"School Phone: {school_phone} | Email: {school_email}", fill="#E2E8F0", anchor="mm")
        draw.text((center_x, 920), "PROPERTY OF INSTITUTION - IF FOUND RETURN TO PRINCIPAL OFFICE", fill="#94A3B8", anchor="mm")
        draw.text((center_x, 948), f"HMAC Verified Token: {sig}", fill="#38BDF8", anchor="mm")

        return card

    # ---------------- 2. FACULTY & STAFF OFFICIAL CARD ----------------
    @classmethod
    def create_staff_card(
        cls,
        emp_id: str,
        staff_name: str,
        designation: str,
        bps_scale: str,
        department: str,
        cnic_no: str,
        official_email: str,
        mobile_no: str,
        emergency_contact: str,
        blood_group: str = "O+",
        institution_name: str = "GOVERNMENT HIGH SCHOOL",
        school_phone: str = "+92 91 1234567"
    ) -> Image.Image:
        emp_id = cls._clean_str(emp_id, "EMP-001")
        staff_name = cls._clean_str(staff_name, "STAFF")
        designation = cls._clean_str(designation, "Teacher")
        bps_scale = cls._clean_str(bps_scale, "16")
        department = cls._clean_str(department, "Academics")
        cnic_no = cls._clean_str(cnic_no, "N/A")
        official_email = cls._clean_str(official_email, "staff@school.edu.pk")
        mobile_no = cls._clean_str(mobile_no, "N/A")
        emergency_contact = cls._clean_str(emergency_contact, "N/A")
        blood_group = cls._clean_str(blood_group, "O+")
        institution_name = cls._clean_str(institution_name, "GOVERNMENT SCHOOL")
        school_phone = cls._clean_str(school_phone, "+92 000 0000000")

        width, height = 600, 980
        card = Image.new("RGB", (width, height), "#FFFFFF")
        draw = ImageDraw.Draw(card)

        # Header - Navy Blue
        draw.rectangle([(0, 0), (width, 150)], fill="#1E3A8A")
        draw.rectangle([(0, 150), (width, 160)], fill="#F59E0B")

        draw.text((width // 2, 45), institution_name.upper(), fill="#FFFFFF", anchor="mm")
        draw.text((width // 2, 85), "FACULTY & OFFICIAL STAFF CARD", fill="#DBEAFE", anchor="mm")
        draw.text((width // 2, 120), "EDUCATION & LITERACY DEPARTMENT", fill="#FDE68A", anchor="mm")

        # Staff Avatar
        center_x = width // 2
        avatar_y = 250
        radius = 70
        draw.ellipse([(center_x - radius - 4, avatar_y - radius - 4), (center_x + radius + 4, avatar_y + radius + 4)], fill="#F59E0B")
        draw.ellipse([(center_x - radius, avatar_y - radius), (center_x + radius, avatar_y + radius)], fill="#E2E8F0")
        draw.ellipse([(center_x - 28, avatar_y - 40), (center_x + 28, avatar_y + 10)], fill="#1E3A8A")
        draw.chord([(center_x - 50, avatar_y - 5), (center_x + 50, avatar_y + 65)], 0, 180, fill="#1E3A8A")

        # Chip
        chip_text = f"{designation.upper()} (BPS-{bps_scale})"
        draw.rounded_rectangle([(center_x - 180, 345), (center_x + 180, 380)], radius=17, fill="#1E3A8A")
        draw.text((center_x, 362), chip_text, fill="#FFFFFF", anchor="mm")

        # Staff Name
        draw.text((center_x, 415), staff_name.upper(), fill="#0F172A", anchor="mm")

        # Data Box
        box_top = 445
        draw.rounded_rectangle([(35, box_top), (width - 35, box_top + 205)], radius=12, fill="#F8FAFC", outline="#E2E8F0", width=2)

        staff_fields = [
            ("Personal / Emp ID :", emp_id),
            ("Department / Cadre:", department),
            ("CNIC Number       :", cnic_no),
            ("Official Email    :", official_email),
            ("Official Phone    :", mobile_no),
            ("Emergency Contact :", emergency_contact),
            ("Blood Group       :", blood_group)
        ]

        y_offset = box_top + 18
        for label, val in staff_fields:
            draw.text((50, y_offset), label, fill="#64748B")
            val_color = "#DC2626" if "Blood" in label else "#0F172A"
            draw.text((230, y_offset), str(val), fill=val_color)
            y_offset += 26

        # Signed QR Code
        raw_body = f"STAFF|{emp_id}|{staff_name}|{designation}|{department}|{mobile_no}"
        sig = cls.sign_payload(raw_body)
        signed_token = f"{raw_body}#{sig}"

        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=2)
        qr.add_data(signed_token)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#1E3A8A", back_color="white").convert("RGB").resize((135, 135))
        card.paste(qr_img, (center_x - 67, 675))

        draw.text((center_x, 830), "AUTHENTICATED FACULTY ATTENDANCE TOKEN", fill="#64748B", anchor="mm")

        # Footer
        draw.rectangle([(0, 860), (width, height)], fill="#0F172A")
        draw.text((center_x, 888), f"School Gate Desk: {school_phone} | Authorized Authority Signature", fill="#E2E8F0", anchor="mm")
        draw.text((center_x, 920), "OFFICIAL GOVERNMENT PROPERTY - VALID FOR CAMPUS ACCESS", fill="#94A3B8", anchor="mm")
        draw.text((center_x, 948), f"HMAC Verified Digital Token: {sig}", fill="#38BDF8", anchor="mm")

        return card

    # ---------------- 3. BULK ZIP BUILDERS (CRASH-PROOF) ----------------
    @classmethod
    def generate_bulk_student_cards_zip(cls, df: pd.DataFrame, school_name: str, school_phone: str, school_email: str) -> bytes:
        col_map = {str(c).strip().lower(): c for c in df.columns}
        
        adm_col = next((col_map[c] for c in col_map if "admission" in c or "adm" in c or "id" in c), None)
        roll_col = next((col_map[c] for c in col_map if "roll" in c), None)
        name_col = next((col_map[c] for c in col_map if "student" in c or "name" in c), None)
        father_col = next((col_map[c] for c in col_map if "father" in c), None)
        class_col = next((col_map[c] for c in col_map if "class" in c or "grade" in c), None)
        sec_col = next((col_map[c] for c in col_map if "sec" in c), None)
        blood_col = next((col_map[c] for c in col_map if "blood" in c), None)
        emg_col = next((col_map[c] for c in col_map if "emergency" in c or "contact" in c or "phone" in c), None)

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            for idx, r in df.iterrows():
                adm = cls._clean_str(r[adm_col] if adm_col else None, f"ADM-{idx+1001}")
                roll = cls._clean_str(r[roll_col] if roll_col else None, str(idx+1))
                name = cls._clean_str(r[name_col] if name_col else None, f"Student_{idx+1}")
                father = cls._clean_str(r[father_col] if father_col else None, "Guardian")
                c_name = cls._clean_str(r[class_col] if class_col else None, "Class 10th")
                sec = cls._clean_str(r[sec_col] if sec_col else None, "A")
                bld = cls._clean_str(r[blood_col] if blood_col else None, "O+")
                emg = cls._clean_str(r[emg_col] if emg_col else None, "+92 300 0000000")

                card = cls.create_student_card(
                    admission_no=adm,
                    roll_no=roll,
                    student_name=name,
                    father_name=father,
                    class_name=c_name,
                    section=sec,
                    blood_group=bld,
                    emergency_contact=emg,
                    school_name=school_name,
                    school_phone=school_phone,
                    school_email=school_email
                )
                b = io.BytesIO()
                card.save(b, format="PNG")
                
                # Sanitize filename
                raw_filename = f"{c_name}_{roll}_{name}"
                safe_name = "".join(c for c in raw_filename if c.isalnum() or c in (' ', '_', '-')).strip()
                z.writestr(f"{safe_name}.png", b.getvalue())

        zip_buf.seek(0)
        return zip_buf.getvalue()

    @classmethod
    def generate_bulk_staff_cards_zip(cls, df: pd.DataFrame, school_name: str, school_phone: str) -> bytes:
        col_map = {str(c).strip().lower(): c for c in df.columns}

        id_col = next((col_map[c] for c in col_map if "emp" in c or "id" in c or "personal" in c), None)
        name_col = next((col_map[c] for c in col_map if "name" in c or "teacher" in c), None)
        desig_col = next((col_map[c] for c in col_map if "desig" in c or "post" in c or "role" in c), None)
        bps_col = next((col_map[c] for c in col_map if "bps" in c or "scale" in c or "grade" in c), None)
        dept_col = next((col_map[c] for c in col_map if "dept" in c or "subject" in c), None)
        cnic_col = next((col_map[c] for c in col_map if "cnic" in c), None)
        email_col = next((col_map[c] for c in col_map if "email" in c), None)
        phone_col = next((col_map[c] for c in col_map if "phone" in c or "mobile" in c), None)
        emg_col = next((col_map[c] for c in col_map if "emergency" in c), None)
        blood_col = next((col_map[c] for c in col_map if "blood" in c), None)

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            for idx, r in df.iterrows():
                e_id = cls._clean_str(r[id_col] if id_col else None, f"EMP-{idx+501}")
                t_name = cls._clean_str(r[name_col] if name_col else None, f"Teacher_{idx+1}")
                desig = cls._clean_str(r[desig_col] if desig_col else None, "Subject Specialist")
                bps = cls._clean_str(r[bps_col] if bps_col else None, "16")
                dept = cls._clean_str(r[dept_col] if dept_col else None, "Academics")
                cnic = cls._clean_str(r[cnic_col] if cnic_col else None, "17301-0000000-0")
                email = cls._clean_str(r[email_col] if email_col else None, f"staff{idx+1}@school.edu.pk")
                phone = cls._clean_str(r[phone_col] if phone_col else None, "+92 300 0000000")
                emg = cls._clean_str(r[emg_col] if emg_col else None, "+92 301 0000000")
                blood = cls._clean_str(r[blood_col] if blood_col else None, "O+")

                card = cls.create_staff_card(
                    emp_id=e_id,
                    staff_name=t_name,
                    designation=desig,
                    bps_scale=bps,
                    department=dept,
                    cnic_no=cnic,
                    official_email=email,
                    mobile_no=phone,
                    emergency_contact=emg,
                    blood_group=blood,
                    institution_name=school_name,
                    school_phone=school_phone
                )
                b = io.BytesIO()
                card.save(b, format="PNG")
                
                raw_filename = f"{desig}_{t_name}"
                safe_name = "".join(c for c in raw_filename if c.isalnum() or c in (' ', '_', '-')).strip()
                z.writestr(f"{safe_name}.png", b.getvalue())

        zip_buf.seek(0)
        return zip_buf.getvalue()
