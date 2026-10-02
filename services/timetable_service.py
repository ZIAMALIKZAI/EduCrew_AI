import pandas as pd
from typing import Dict, List, Tuple

class TimetableService:
    """
    Automated Multi-Class School Timetable Generator:
    - 6-Day school week (Monday to Saturday).
    - Mon, Tue, Wed, Thu, Sat: 8 periods.
    - Friday: 5 periods.
    - Farm Master: Always takes Period 1 from Monday to Saturday.
    - Consistency Rule: If a teacher visits the same class multiple days, 
      they are placed in the SAME period slot across those days.
    - Max 1 period per teacher per class per day.
    - Zero teacher conflict across different classes.
    """

    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    @classmethod
    def get_day_periods(cls, day: str) -> int:
        return 5 if day == "Friday" else 8

    @classmethod
    def generate_timetable(cls, df: pd.DataFrame) -> Tuple[Dict[str, pd.DataFrame], str]:
        # Normalize columns for flexible file uploads
        col_map = {c.strip().lower(): c for c in df.columns}
        
        req_cols = ["teacher_name", "designation", "periods_per_week", "subject"]
        matched = {}
        for req in req_cols:
            found = next((col_map[c] for c in col_map if req.replace("_", "") in c.replace("_", "").replace(" ", "")), None)
            if not found:
                return {}, f"Missing column: Please ensure your file has {req.replace('_', ' ').title()}."
            matched[req] = found

        # Class column is optional; defaults to "Class 10" if not present
        class_col = next((col_map[c] for c in col_map if "class" in c.replace("_", "").replace(" ", "") or "grade" in c), None)

        # 1. Parse teacher records
        teacher_entries = []
        farm_master = None

        for row in df.to_dict(orient="records"):
            t_name = str(row[matched["teacher_name"]]).strip()
            desig = str(row[matched["designation"]]).strip()
            subj = str(row[matched["subject"]]).strip()
            cls_assigned = str(row[class_col]).strip() if class_col and pd.notna(row[class_col]) else "Class 10"
            
            try:
                periods = int(row[matched["periods_per_week"]])
            except (ValueError, TypeError):
                periods = 0

            is_farm = "farm" in desig.lower() or "farm master" in desig.lower()

            entry = {
                "teacher": t_name,
                "designation": desig,
                "subject": subj,
                "target_class": cls_assigned,
                "periods": periods,
                "is_farm": is_farm
            }

            if is_farm and not farm_master:
                farm_master = entry

            teacher_entries.append(entry)

        # Identify all distinct classes
        classes = sorted(list({t["target_class"] for t in teacher_entries}))

        # 2. Initialize Master Schedule: Class -> Day -> Period (0-7)
        # Structure: master_schedule[cls][day][period_idx] = assignment_dict
        master_schedule = {
            cls: {
                day: [{"period": p + 1, "teacher": "FREE", "subject": "-", "designation": "-"} 
                      for p in range(cls.get_day_periods(day))]
                for day in cls.DAYS
            }
            for cls in classes
        }

        # 3. Rule 1: Farm Master gets Period 1 on all 6 days (Mon-Sat)
        if farm_master:
            fm_class = farm_master["target_class"]
            for day in cls.DAYS:
                master_schedule[fm_class][day][0] = {
                    "period": 1,
                    "teacher": farm_master["teacher"],
                    "subject": farm_master["subject"],
                    "designation": farm_master["designation"]
                }
                farm_master["periods"] = max(0, farm_master["periods"] - 1)

        # 4. Schedule other teachers with the Same-Period Consistency Rule
        # Sort teachers: highest workload first to allocate prime fixed slots
        teacher_entries.sort(key=lambda x: x["periods"], reverse=True)

        for entry in teacher_entries:
            rem_periods = entry["periods"]
            if rem_periods <= 0:
                continue

            target_cls = entry["target_class"]
            t_name = entry["teacher"]
            is_fm = entry["is_farm"]

            # Possible period slots: skip Period 1 (index 0) if Farm Master is active
            available_slots = list(range(1 if farm_master else 0, 8))

            # Pick the best consistent period slot for this teacher-class pair
            chosen_slot = None
            for p_slot in available_slots:
                # Count on how many days this slot is free for both this class and this teacher
                free_days_count = 0
                for day in cls.DAYS:
                    # Slot must exist on this day (Friday only has slots 0-4)
                    if p_slot >= cls.get_day_periods(day):
                        continue
                    
                    # Check class slot is empty
                    if master_schedule[target_cls][day][p_slot]["teacher"] != "FREE":
                        continue

                    # Check teacher is not already booked in another class in the same day & slot
                    teacher_busy = False
                    for other_cls in classes:
                        if master_schedule[other_cls][day][p_slot]["teacher"] == t_name:
                            teacher_busy = True
                            break

                    if not teacher_busy:
                        free_days_count += 1

                # If this slot can accommodate all or most of the weekly demand, lock it in
                if free_days_count >= min(rem_periods, 4):
                    chosen_slot = p_slot
                    break

            # Fallback if no single slot was ideal
            if chosen_slot is None:
                chosen_slot = available_slots[0]

            # Assign teacher across different days in the chosen consistent period slot
            for day in cls.DAYS:
                if rem_periods <= 0:
                    break

                if chosen_slot >= cls.get_day_periods(day):
                    continue

                # Check if this class is free in the chosen slot
                if master_schedule[target_cls][day][chosen_slot]["teacher"] == "FREE":
                    # Check teacher isn't busy in another class
                    is_busy = any(master_schedule[c][day][chosen_slot]["teacher"] == t_name for c in classes)
                    if not is_busy:
                        master_schedule[target_cls][day][chosen_slot] = {
                            "period": chosen_slot + 1,
                            "teacher": t_name,
                            "subject": entry["subject"],
                            "designation": entry["designation"]
                        }
                        rem_periods -= 1

            # If any periods remain (e.g. slots clashed), place them in alternative free slots (1 per day)
            if rem_periods > 0:
                for day in cls.DAYS:
                    if rem_periods <= 0:
                        break
                    # Ensure teacher doesn't already have a period with this class today
                    already_in_day = any(master_schedule[target_cls][day][p]["teacher"] == t_name 
                                         for p in range(cls.get_day_periods(day)))
                    if already_in_day:
                        continue

                    for alt_slot in range(cls.get_day_periods(day)):
                        if master_schedule[target_cls][day][alt_slot]["teacher"] == "FREE":
                            busy = any(master_schedule[c][day][alt_slot]["teacher"] == t_name for c in classes)
                            if not busy:
                                master_schedule[target_cls][day][alt_slot] = {
                                    "period": alt_slot + 1,
                                    "teacher": t_name,
                                    "subject": entry["subject"],
                                    "designation": entry["designation"]
                                }
                                rem_periods -= 1
                                break

        # 5. Format output into clean DataFrames grouped by Class and Day
        day_dfs = {}
        for cls_name in classes:
            for day in cls.DAYS:
                sheet_key = f"{cls_name} - {day}" if len(classes) > 1 else day
                day_rows = []
                for item in master_schedule[cls_name][day]:
                    day_rows.append({
                        "Period": f"Period {item['period']}",
                        "Class": cls_name,
                        "Teacher": item["teacher"],
                        "Subject": item["subject"],
                        "Designation": item["designation"]
                    })
                day_dfs[sheet_key] = pd.DataFrame(day_rows)

        return day_dfs, ""
