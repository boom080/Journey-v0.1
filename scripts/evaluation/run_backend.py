from scripts.evaluation.runtime import configure
configure(False)
import pytest
raise SystemExit(pytest.main(['backend/tests','evals/test_text_provider_acceptance.py','evals/test_rag_eval.py','evals/test_agent_v2_provider_acceptance.py','evals/test_agent_v3_provider_acceptance.py','-q','-p','no:cacheprovider','--junitxml=evaluation/raw/backend.xml']))
