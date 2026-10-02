import pandas as pd
from typing import Dict, List, Tuple

class TimetableService:
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    @classmethod
    def get_day_periods(cls, day: str) -> int:
        return 5 if day == "Friday" else 8

    @classmethod
    def generate_timetable(cls, df: pd.DataFrame, default_class_name: str = "Class 10th") -> Tuple[Dict[str, pd.DataFrame], str]:
        col_map = {str(c).strip().lower(): c for c in df.columns}
        
        req_cols = ["teacher_name", "designation", "periods_per_week", "subject"]
        matched = {}
        for req in req_cols:
            found = next((col_map[c] for c in col_map if req.replace("_", "") in c.replace("_", "").replace(" ", "")), None)
            if not found:
                return {}, f"Missing column: Please ensure your file has '{req.replace('_', ' ').title()}'."
            matched[req] = found

        class_col_candidates = ["class", "classname", "class_name", "grade", "section", "standard", "cls"]
        class_col = None
        for cand in class_col_candidates:
            found = next((col_map[c] for c in col_map if cand in c.replace("_", "").replace(" ", "")), None)
            if found:
                class_col = found
                break

        teacher_entries = []
        farm_master = None

        for row in df.to_dict(orient="records"):
            t_name = str(row[matched["teacher_name"]]).strip()
            desig = str(row[matched["designation"]]).strip()
            subj = str(row[matched["subject"]]).strip()

            if class_col and pd.notna(row[class_col]) and str(row[class_col]).strip():
                cls_assigned = str(row[class_col]).strip()
            else:
                cls_assigned = default_class_name.strip()
            
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

        classes = sorted(list({t["target_class"] for t in teacher_entries if t["target_class"]}))
        if not classes:
            classes = [default_class_name]

        master_schedule = {
            c_name: {
                day: [{
                    "period": p + 1,
                    "class": c_name,
                    "teacher": "FREE",
                    "subject": "-",
                    "designation": "-"
                } for p in range(cls.get_day_periods(day))]
                for day in cls.DAYS
            }
            for c_name in classes
        }

        if farm_master:
            fm_class = farm_master["target_class"]
            for day in cls.DAYS:
                master_schedule[fm_class][day][0] = {
                    "period": 1,
                    "class": fm_class,
                    "teacher": farm_master["teacher"],
                    "subject": farm_master["subject"],
                    "designation": farm_master["designation"]
                }
                farm_master["periods"] = max(0, farm_master["periods"] - 1)

        teacher_entries.sort(key=lambda x: x["periods"], reverse=True)

        for entry in teacher_entries:
            rem_periods = entry["periods"]
            if rem_periods <= 0:
                continue

            target_cls = entry["target_class"]
            t_name = entry["teacher"]
            available_slots = list(range(1 if farm_master else 0, 8))

            chosen_slot = None
            for p_slot in available_slots:
                free_days_count = 0
                for day in cls.DAYS:
                    if p_slot >= cls.get_day_periods(day):
                        continue
                    if master_schedule[target_cls][day][p_slot]["teacher"] != "FREE":
                        continue

                    teacher_busy = any(master_schedule[oc][day][p_slot]["teacher"] == t_name for oc in classes)
                    if not teacher_busy:
                        free_days_count += 1

                if free_days_count >= min(rem_periods, 4):
                    chosen_slot = p_slot
                    break

            if chosen_slot is None:
                chosen_slot = available_slots[0]

            for day in cls.DAYS:
                if rem_periods <= 0:
                    break
                if chosen_slot >= cls.get_day_periods(day):
                    continue

                if master_schedule[target_cls][day][chosen_slot]["teacher"] == "FREE":
                    busy = any(master_schedule[oc][day][chosen_slot]["teacher"] == t_name for oc in classes)
                    if not busy:
                        master_schedule[target_cls][day][chosen_slot] = {
                            "period": chosen_slot + 1,
                            "class": target_cls,
                            "teacher": t_name,
                            "subject": entry["subject"],
                            "designation": entry["designation"]
                        }
                        rem_periods -= 1

            if rem_periods > 0:
                for day in cls.DAYS:
                    if rem_periods <= 0:
                        break
                    already_in_day = any(master_schedule[target_cls][day][p]["teacher"] == t_name for p in range(cls.get_day_periods(day)))
                    if already_in_day:
                        continue

                    for alt_slot in range(cls.get_day_periods(day)):
                        if master_schedule[target_cls][day][alt_slot]["teacher"] == "FREE":
                            busy = any(master_schedule[oc][day][alt_slot]["teacher"] == t_name for oc in classes)
                            if not busy:
                                master_schedule[target_cls][day][alt_slot] = {
                                    "period": alt_slot + 1,
                                    "class": target_cls,
                                    "teacher": t_name,
                                    "subject": entry["subject"],
                                    "designation": entry["designation"]
                                }
                                rem_periods -= 1
                                break

        day_dfs = {}
        for c_name in classes:
            for day in cls.DAYS:
                tab_key = f"{c_name} - {day}" if len(classes) > 1 else day
                day_rows = []
                for item in master_schedule[c_name][day]:
                    day_rows.append({
                        "Class": item["class"],
                        "Period": f"Period {item['period']}",
                        "Teacher Name": item["teacher"],
                        "Subject": item["subject"],
                        "Designation": item["designation"]
                    })
                day_dfs[tab_key] = pd.DataFrame(day_rows)

        return day_dfs, ""
