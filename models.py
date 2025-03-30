from datetime import datetime
from dataclasses import dataclass
from typing import List

@dataclass
class HabitLog:
    habit: str
    completed: bool

@dataclass
class DailyHabitLog:
    date: datetime
    habits: List[HabitLog]

@dataclass
class WeeklyHabitLog:
    week: str
    habits: List[HabitLog]

@dataclass
class Habit:
    name: str
    type: str # daily, weekly
