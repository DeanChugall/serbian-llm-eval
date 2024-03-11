"""
Latent Retrieval for Weakly Supervised Open Domain Question Answering
https://arxiv.org/pdf/1906.00300.pdf

Natural Questions: a Benchmark for Question Answering Research
https://storage.googleapis.com/pub-tools-public-publication-data/pdf/1f7b46b5378d757553d3e92ead36bda2e4254244.pdf

The NQ-Open task, introduced by Lee et. al. 2019, is an open-domain question
answering benchmark that is derived from Natural Questions. The goal is to predict
an English answer string for an input English question. All questions can be
answered using the contents of English Wikipedia.

Homepage: https://github.com/google-research-datasets/natural-questions/tree/master/nq_open
"""
import regex
import string
from lm_eval.base import Task, rf
from lm_eval.metrics import mean

_CITATION = """
@inproceedings{lee-etal-2019-latent,
    title = "Latent Retrieval for Weakly Supervised Open Domain Question Answering",
    author = "Lee, Kenton  and
      Chang, Ming-Wei  and
      Toutanova, Kristina",
    booktitle = "Proceedings of the 57th Annual Meeting of the Association for Computational Linguistics",
    month = jul,
    year = "2019",
    address = "Florence, Italy",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/P19-1612",
    doi = "10.18653/v1/P19-1612",
    pages = "6086--6096",
    abstract = "Recent work on open domain question answering (QA) assumes strong supervision of the supporting evidence and/or assumes a blackbox information retrieval (IR) system to retrieve evidence candidates. We argue that both are suboptimal, since gold evidence is not always available, and QA is fundamentally different from IR. We show for the first time that it is possible to jointly learn the retriever and reader from question-answer string pairs and without any IR system. In this setting, evidence retrieval from all of Wikipedia is treated as a latent variable. Since this is impractical to learn from scratch, we pre-train the retriever with an Inverse Cloze Task. We evaluate on open versions of five QA datasets. On datasets where the questioner already knows the answer, a traditional IR system such as BM25 is sufficient. On datasets where a user is genuinely seeking an answer, we show that learned retrieval is crucial, outperforming BM25 by up to 19 points in exact match.",
}
"""


class NQOpen(Task):
    VERSION = 0
    DATASET_PATH = "nq_open"
    DATASET_NAME = None

    def __init__(self, **kwargs):
        language = kwargs.get("language", "English")
        self._language = language
        if language == "Serbian":
            self.DATASET_PATH = "gordicaleksa/serbian-llm-eval-v1"
            self.DATASET_NAME = "nq_open"
        elif language == "Slovenian":
            self.DATASET_PATH = "gordicaleksa/slovenian-llm-eval-v0"
            self.DATASET_NAME = "nq_open"
        super().__init__(**kwargs)

    def has_training_docs(self):
        return True

    def has_validation_docs(self):
        return True

    def has_test_docs(self):
        return False

    def training_docs(self):
        return self.dataset["train"]

    def validation_docs(self):
        return self.dataset["test"] if self._language in ["Serbian", "Slovenian"] else self.dataset["validation"]

    def test_docs(self):
        raise NotImplementedError()

    def doc_to_text(self, doc):
        if self._language == "Serbian":
            return f"Pitanje: {doc['question']}\nOdgovor:"
        elif self._language == "Slovenian":
            return f"Vprašanje: {doc['question']}\nOdgovor:"
        else:
            return f"Q: {doc['question']}\nA:"

    def should_decontaminate(self):
        return True

    def doc_to_decontamination_query(self, doc):
        return doc["question"]

    def doc_to_target(self, doc):
        return " " + doc["answer"][0]

    def construct_requests(self, doc, ctx):
        """Uses RequestFactory to construct Requests and returns an iterable of
        Requests which will be sent to the LM.
        :param doc:
                The document as returned from training_docs, validation_docs, or test_docs.
        :param ctx: str
                The context string, generated by fewshot_context. This includes the natural
                language description, as well as the few shot examples, and the question
                part of the document for `doc`.
        """
        continuation = rf.greedy_until(ctx, {"until": ["\n", ".", ","]})
        return continuation

    def _normalize_answer(self, text):
        # Lowercase and remove punctuation, strip whitespace
        text = text.strip().lower().translate(str.maketrans("", "", string.punctuation))

        # Remove articles, resulting in duplicate whitespace
        text = regex.sub(r"\b(a|an|the)\b", " ", text)

        # Remove duplicate whitespace
        text = " ".join(text.split())

        return text

    def process_results(self, doc, results):
        """Take a single document and the LM results and evaluates, returning a
        dict where keys are the names of submetrics and values are the values of
        the metric for that one document

        :param doc:
            The document as returned from training_docs, validation_docs, or test_docs.
        :param results:
            The results of the requests created in construct_requests.
        """
        continuation = self._normalize_answer(results[0])
        answers = [self._normalize_answer(answer) for answer in doc["answer"]]

        return {"em": float(continuation in answers)}

    def aggregation(self):
        """
        :returns: {str: [float] -> float}
            A dictionary where keys are the names of submetrics and values are
            functions that aggregate a list of metrics
        """
        return {
            "em": mean,
        }

    def higher_is_better(self):
        """
        :returns: {str: bool}
            A dictionary where keys are the names of submetrics and values are
            whether a higher value of the submetric is better
        """
        return {
            "em": True,
        }
