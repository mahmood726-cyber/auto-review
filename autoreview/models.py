from dataclasses import dataclass, field


@dataclass
class PICOQuery:
    population: str
    intervention: str
    comparator: str
    outcome: str
    study_design: str = "RCT"

    @property
    def question(self):
        return (f"In {self.population}, does {self.intervention} vs "
                f"{self.comparator} affect {self.outcome}?")


@dataclass
class TrialRecord:
    nct_id: str
    title: str
    status: str = ""
    phase: str = ""
    enrollment: int = 0
    start_date: str = ""
    completion_date: str = ""
    sponsor: str = ""
    conditions: list[str] = field(default_factory=list)
    interventions: list[str] = field(default_factory=list)
    primary_outcome: str = ""
    results_posted: bool = False
    # Extracted effect data (if available)
    effect_size: float | None = None
    ci_lo: float | None = None
    ci_hi: float | None = None
    se: float | None = None
    measure: str = ""  # "HR", "OR", "RR", "MD"
    events_intervention: int | None = None
    events_control: int | None = None
    n_intervention: int | None = None
    n_control: int | None = None
    source: str = "ctgov"


@dataclass
class ScreeningResult:
    included: list[TrialRecord] = field(default_factory=list)
    excluded: list[tuple[str, str]] = field(default_factory=list)  # (nct_id, reason)
    n_identified: int = 0
    n_screened: int = 0
    n_eligible: int = 0
    n_included: int = 0


@dataclass
class PooledResult:
    theta: float = 0.0
    se: float = 0.0
    ci_lo: float = 0.0
    ci_hi: float = 0.0
    p_value: float = 1.0
    tau2: float = 0.0
    i2: float = 0.0
    k: int = 0
    measure: str = ""
    method: str = "DL"
    significant: bool = False
    direction: str = ""


@dataclass
class GRADEAssessment:
    risk_of_bias: str = "not serious"
    inconsistency: str = "not serious"
    indirectness: str = "not serious"
    imprecision: str = "not serious"
    publication_bias: str = "undetected"
    overall: str = "High"
    explanation: str = ""


@dataclass
class AutoReviewResult:
    query: PICOQuery = field(default_factory=lambda: PICOQuery("", "", "", ""))
    screening: ScreeningResult = field(default_factory=ScreeningResult)
    pooled: PooledResult = field(default_factory=PooledResult)
    grade: GRADEAssessment = field(default_factory=GRADEAssessment)
    manuscript: str = ""
    prisma_flow: str = ""
    forest_data: list[dict] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    certification: str = ""
