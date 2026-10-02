import pandas as pd
from typing import Dict, Tuple

class TimetableService:
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    @classmethod
    def get_day_periods(cls, day: str) -> int:
        return 5 if day == "Friday" else 8

    @classmethod
    def generate_timetable(cls, df: pd.DataFrame) -> Tuple[Dict[str, pd.DataFrame], str]:
        col_map = {c.strip().lower(): c for c in df.columns}
        req_cols = ["teacher_name", "designation", "periods_per_week", "subject"]
        matched = {}
        for req in req_cols:
            found = next((col_map[c] for c in col_map if req.replace("_", "") in c.replace("_", "").replace(" ", "")), None)
            if not found:
                return {}, "Missing column: Please ensure Teacher Name, Designation, Periods Per Week, and Subject exist."
            matched[req] = found

        teachers = df.to_dict(orient="records")
        schedule = {}
        for day in cls.DAYS:
            total_p = cls.get_day_periods(day)
            schedule[day] = [{"period": p + 1, "teacher": "FREE", "subject": "-", "designation": "-"} for p in range(total_p)]

        demand = []
        farm_master = None
        for t in teachers:
            name = str(t[matched["teacher_name"]]).strip()
            desig = str(t[matched["designation"]]).strip()
            subj = str(t[matched["subject"]]).strip()
            try:
                periods = int(t[matched["periods_per_week"]])
            except (ValueError, TypeError):
                periods = 0

            is_farm = "farm" in desig.lower() or "farm master" in desig.lower()
            record = {"name": name, "desig": desig, "subject": subj, "remaining": periods, "is_farm": is_farm}
            if is_farm and not farm_master:
                farm_master = record
            demand.append(record)

        # Rule: Farm Master gets 1st period of every day (Monday to Saturday)
        if farm_master:
            for day in cls.DAYS:
                schedule[day][0] = {
                    "period": 1,
                    "teacher": farm_master["name"],
                    "subject": farm_master["subject"],
                    "designation": farm_master["desig"]
                }
                farm_master["remaining"] = max(0, farm_master["remaining"] - 1)

        # Distribute remaining periods
        for day in cls.DAYS:
            start_p = 1 if farm_master else 0
            total_p = cls.get_day_periods(day)
            for p_idx in range(start_p, total_p):
                candidates = [t for t in demand if t["remaining"] > 0]
                if not candidates:
                    continue
                candidates.sort(key=lambda x: x["remaining"], reverse=True)
                chosen = candidates[0]
                schedule[day][p_idx] = {
                    "period": p_idx + 1,
                    "teacher": chosen["name"],
                    "subject": chosen["subject"],
                    "designation": chosen["desig"]
                }
                chosen["remaining"] -= 1

        day_dfs = {}
        for day in cls.DAYS:
            day_data = []
            for item in schedule[day]:
                day_data.append({
                    "Period": f"Period {item['period']}",
                    "Teacher": item["teacher"],
                    "Subject": item["subject"],
                    "Designation": item["designation"]
                })
            day_dfs[day] = pd.DataFrame(day_data)

        return day_dfs, ""
