from Lab_8 import ResumeParser
from Lab_8 import MCQGenerator
from Lab_8 import CandidateScorer
from Lab_8 import InterviewEvaluator
from Lab_8 import RecruitmentSystem
import pytest

resumeSingleSkill5Expr = ResumeParser("I know sql and i have 5 years experience");
resumeMultiSkill0Expr = ResumeParser("I know sql as well as java");
resumeNoSkill5_5Expr = ResumeParser("I know commnication as well as presentation with 5.5 years experience");
resumeUpperInputNegExp = ResumeParser("I know SQL and have -1 year experience");

def test_single_extract_skills():
	assert resumeSingleSkill5Expr.extract_skills() == ["sql"]
	
def test_multi_extract_skills():
	assert resumeMultiSkill0Expr.extract_skills() == ["java", "sql"]
	
def test_none_extract_skills():
	assert resumeNoSkill5_5Expr.extract_skills() == []
	
def test_upper_input_extract_skills():
	assert resumeUpperInputNegExp.extract_skills() == ["sql"]
	
def test_extract_experience():
	assert resumeSingleSkill5Expr.extract_experience() == 5

def test_zero_extract_experience():
	assert resumeMultiSkill0Expr.extract_experience() == 0
	
def test_float_expr_extract_experience():
	assert resumeNoSkill5_5Expr.extract_experience() == 5.5
	
def test_neg_expr_extract_experience():
	assert resumeUpperInputNegExp.extract_experience() == 0
	


noskillMCQ = MCQGenerator([])
easyskillMCQ = MCQGenerator(["sql"])	
easyskillMCQ2 = MCQGenerator(["sql"], "easy")
easytwoskillMCQ2 = MCQGenerator(["sql", "java"], "easy")
mediumskillMCQ = MCQGenerator(["sql"], "medium")	
hardskillMCQ = MCQGenerator(["sql"], "hard")	
unkownDifficultyMCQ = MCQGenerator(["sql"], "Extreme")	

def test_no_skills_Mcq():
	with pytest.raises(ValueError, match="No skills provided"):
		noskillMCQ.generate_question()

def test_easy_Mcq_default():
	assert easyskillMCQ.generate_question() == "What is sql?"
	
def test_easy_Mcq():
	assert easyskillMCQ2.generate_question() == "What is sql?"

def testtwoskill_easy_Mcq():
	assert easytwoskillMCQ2.generate_question() == "What is sql?"
		
def test_medium_Mcq():
	assert mediumskillMCQ.generate_question() == "Explain key concepts of sql."
	
def test_hard_Mcq():
	assert hardskillMCQ.generate_question() == "Design a system using sql."
	
def test_extreme_Mcq():
	with pytest.raises(ValueError, match="Invalid difficulty level"):
		unkownDifficultyMCQ.generate_question()
		


candidateScorerNoskills = CandidateScorer([], 0);
candidateScoreroneskills = CandidateScorer(["sql"], 0);
candidateScorertwoskillsNoexpr = CandidateScorer(["sql", "java"], 0);
candidateScorertwoskills6Expr = CandidateScorer(["sql", "java"], 6);
candidateScorertwoskills5Expr = CandidateScorer(["sql", "java"], 5);
candidateScorertwoskills3Expr = CandidateScorer(["sql", "java"], 3);
candidateScorertwoskills2Expr = CandidateScorer(["sql", "java"], 2);
candidateScorertwoskillsNegExpr = CandidateScorer(["sql", "java"], -1);

def test_calculate_score_Noskills_Noexpr():
	assert candidateScorerNoskills.calculate_score() == 10
	
def test_calculate_score_oneskills_Noexpr():
	assert candidateScoreroneskills.calculate_score() == 20	
	
def test_calculate_score_twoskills_Noexpr():
	assert candidateScorertwoskillsNoexpr.calculate_score() == 30
	
def test_calculate_score_twoskills_6expr():
	assert candidateScorertwoskills6Expr.calculate_score() == 50
	
def test_calculate_score_twoskills_5expr():
	assert candidateScorertwoskills5Expr.calculate_score() == 40
	
def test_calculate_score_twoskills_3expr():
	assert candidateScorertwoskills2Expr.calculate_score() == 30
	
def test_calculate_score_twoskills_Negexpr():
	assert candidateScorertwoskillsNegExpr.calculate_score() == 30
	
	
interviewEvaluator = InterviewEvaluator()


def test_interviewEvaluatorNoAnswer():
	with pytest.raises(ValueError, match="Answers cannot be empty"):
		interviewEvaluator.evaluate([])
		
def test_interviewEvaluatorEmptyAnswer():
	assert interviewEvaluator.evaluate([" "]) == 5
	
def test_interviewEvaluatorOneLine():
	assert interviewEvaluator.evaluate(["Good"]) == 5
	
def test_interviewEvaluatoronePara():
	assert interviewEvaluator.evaluate(["He is very good at sql and Java also knows the python"]) == 10
	
def test_interviewEvaluatoronePara20():
	assert interviewEvaluator.evaluate(["He is very good at s"]) == 5
	
def test_interviewEvaluatoroneParaonegood():
	assert interviewEvaluator.evaluate(["He is very good at sql and Java also knows the python", "Best"]) == 15
	
	
	
recruitmentSystem = RecruitmentSystem("I know sql and i have 5 years experience", "easy")
recruitmentSystem2 = RecruitmentSystem("I know sql and java and i have 6 years experience", "medium")
recruitmentSystemError = RecruitmentSystem("I know commnication and i have 5 years experience", "easy")

def test_recruitmentSystem():
	assert recruitmentSystem.process() == {
            "skills": ["sql"],
            "experience": 5,
            "score": 30,
            "question": "What is sql?"
        }
        
def test_recruitmentSystem_medium():
	assert recruitmentSystem2.process() == {
            "skills": ["java", "sql"],
            "experience": 6,
            "score": 50,
            "question": "Explain key concepts of java."
        }
        
def test_recruitmentSystemError():
	assert recruitmentSystemError.process() == {
            "skills": [],
            "experience": 5,
            "score": 20,
            "question": "No valid question generated"
        }
	
	
		
		
		




	
		
	
