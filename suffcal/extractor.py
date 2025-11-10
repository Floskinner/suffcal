import os
from pathlib import Path
from typing import List, Optional, Union
from paddleocr import PPStructureV3
import json

from huggingface_hub import snapshot_download, login
from llama_cpp import Llama
import dataclasses
from datetime import datetime


@dataclasses.dataclass
class Event:
    # non-default fields first (required by dataclasses)
    src: Union[Path, str]
    original_text: str

    # optional fields with defaults
    title: Optional[str] = None
    time: Optional[str] = None
    location: Optional[str] = None
    date: Optional[datetime] = dataclasses.field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Ensure that `date` is a datetime object.

        If `date` was provided as a string, try to parse it using ISO 8601
        first, then a small set of common formats. If parsing fails, leave
        the field as None.
        """
        if self.date is None:
            return

        # If already a datetime, nothing to do
        if isinstance(self.date, datetime):
            return

        # If it's a string, try to parse
        if not isinstance(self.date, str):
            self.date = None
            return

        def _try_parse(date_str):
            date_str = date_str.strip()
            # Try ISO 8601 first (YYYY-MM-DD or full datetime)
            try:
                # fromisoformat handles 'YYYY-MM-DD' and 'YYYY-MM-DDTHH:MM:SS'
                return datetime.fromisoformat(date_str)
            except Exception:
                pass

            # Try common German/European formats and others
            common_formats = [
                "%d.%m.%Y",
                "%d.%m.%y",
                "%d/%m/%Y",
                "%d/%m/%y",
                "%Y-%m-%d",
                "%Y/%m/%d",
            ]
            for fmt in common_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except Exception:
                    continue

            # As a fallback, attempt a loose parse using the dateutil parser
            try:
                from dateutil import parser as _parser

                return _parser.parse(date_str)
            except Exception:
                # give up — set to None to indicate unknown/invalid date
                return None

        tried = _try_parse(self.date)
        if tried:
            self.date = tried
            return

        # Try adding a year at the end, since they are missing in most of the event
        tried = _try_parse(self.date + f"{datetime.now().year}")
        self.date = tried


class Extractor:
    def __init__(
        self,
        repo_id: str = "TheBloke/CapybaraHermes-2.5-Mistral-7B-GGUF",
        repo_files: List[Path] = [Path("capybarahermes-2.5-mistral-7b.Q4_K_M.gguf")],
        mistral_models_folder: Path = Path.home() / ".cache" / "mistral_models",
        chat_format="llama-2",
        text_recognition_model_name="en_PP-OCRv4_mobile_rec",
        ocr_lang="de",
    ):
        self.repo_id = repo_id
        self.repo_files = repo_files
        self.mistral_models_folder = Path(mistral_models_folder)
        self.chat_format = chat_format
        self.text_recognition_model_name = text_recognition_model_name
        self.ocr_lang = ocr_lang

        self.llm = None
        self.ocr_pipeline = None

        self.__init_ocr()
        self.__init_llm()

    def __init_llm(self):
        # Download files if neededtext_recognition_model_name="en_PP-OCRv4_mobile_rec"
        needed_files = [self.mistral_models_folder / file for file in self.repo_files]
        if not all(file.exists() for file in needed_files):
            if os.getenv("HF_TOKEN"):
                login(token=os.getenv("HF_TOKEN"))
            else:
                print(
                    f"ERROR: Missing Text recognition model! Please provide a HF_TOKEN (Hugging Face) or provide the needed models file of {self.repo_id}: {self.repo_files}"
                )
            self.mistral_models_folder.mkdir(parents=True, exist_ok=True)
            snapshot_download(
                repo_id=self.repo_id,
                allow_patterns=self.repo_files,
                local_dir=self.mistral_models_folder,
            )

        # load the model
        model_file = [file for file in self.mistral_models_folder.glob("*.gguf")][0]
        if not model_file.exists():
            raise FileNotFoundError(
                f"Model file not found in {self.mistral_models_folder}"
            )

        self.llm = Llama(model_path=str(model_file), chat_format=self.chat_format)

    def __init_ocr(self):
        # TODO: Download needed?
        self.ocr_pipeline = PPStructureV3(
            text_recognition_model_name=self.text_recognition_model_name,
            lang=self.ocr_lang,
        )

    def extract(self, image: Path) -> List[Event]:
        for current_try in range(1):
            words = self._do_ocr(image)
            text = " ".join(words)
            ai_result = self.ask_llm(text)
            try:
                ai_result_json = self._parse_ai_response(ai_result)

                events = []
                if isinstance(ai_result_json, list):
                    events = [
                        Event(
                            src=image,
                            title=event.get("Titel"),
                            date=event.get("Datum"),
                            time=event.get("Uhrzeit"),
                            location=event.get("Ort"),
                            original_text=text,
                        )
                        for event in ai_result_json
                    ]
                else:
                    events = [
                        Event(
                            src=image,
                            title=ai_result_json.get("Titel"),
                            date=ai_result_json.get("Datum"),
                            time=ai_result_json.get("Uhrzeit"),
                            location=ai_result_json.get("Ort"),
                            original_text=text,
                        )
                    ]

                return events
            except Exception as error:
                print(
                    f"Try {current_try} - Unable to parse text '{text}' -> '{ai_result}'"
                )
                print(error)

        # return a list with a single Event describing the failure
        return [Event(src=image, original_text=text)]

    def _do_ocr(self, image: Path) -> List[str]:
        outputs = self.ocr_pipeline.predict(str(image))
        for output in outputs:
            try:
                return output.json["res"]["overall_ocr_res"].get("rec_texts", "")
            except Exception as e:
                print(f"Unable to do COR: {e}")
                raise e
        raise RuntimeError("OCR pipeline returned no outputs")

    def ask_llm(self, text: str) -> str:
        # Use lower temperature and a reasonable token budget to reduce
        # hallucinations and truncated outputs. Also provide a few-shot
        # schema example so the model returns strictly the expected JSON.
        prompt_example = '{"Titel": null, "Datum": null, "Uhrzeit": null, "Ort": null}'

        user_instructions = f"""
Extrahiere aus folgendem Text die wichtigsten Informationen zur Veranstaltung(en), insbesondere Titel, Datum, Uhrzeit und Ort.

Antwortformat (wichtig):
- Wenn eine Veranstaltung: gib ein einzelnes JSON-Objekt mit den Schlüsseln 'Titel', 'Datum', 'Uhrzeit', 'Ort'.
- Wenn mehrere: gib eine JSON-Liste von Objekten. Beispiel (Liste): [{prompt_example}]
- Fehlende Informationen -> null.
- Datum: ISO 8601 Format YYYY-MM-DD (oder null).
- Antworte ausschließlich mit gültigem JSON in einer einzigen Zeile, ohne erläuternden Text oder Zeilenumbrüche.
- Erfinde keine Informationen.

Text: {text}
"""

        # llama-cpp-python supports temperature and max_tokens; include them
        # to make outputs more deterministic and allow longer replies.
        try:
            result = self.llm.create_chat_completion(
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "Du bist ein hilfreicher Assistent, der relevante Informationen aus Texten extrahiert.",
                    },
                    {"role": "user", "content": user_instructions},
                ],
                max_tokens=1024,
                temperature=0.0,
                top_p=0.95,
            )
        except TypeError:
            # Some llama-cpp versions may not accept kwargs; fall back to call without them
            print("Falllback, using llm withoit kwargs")
            result = self.llm.create_chat_completion(
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "Du bist ein hilfreicher Assistent, der relevante Informationen aus Texten extrahiert.",
                    },
                    {"role": "user", "content": user_instructions},
                ],
            )
        try:
            return result["choices"][0]["message"]["content"]
        except Exception as error:
            print(f"Unable to parse AI output: {error}")
            raise error

    def _extract_json_substring(self, text: str) -> Optional[str]:
        """Attempt to extract the first balanced JSON object/array from text.

        Returns the substring or None if not found.
        """
        if not text or not isinstance(text, str):
            return None

        # find first { or [ and try to find its matching closing bracket
        for start_idx, ch in enumerate(text):
            if ch not in "{[":
                continue
            open_ch = ch
            close_ch = "}" if ch == "{" else "]"
            depth = 0
            for i in range(start_idx, len(text)):
                if text[i] == open_ch:
                    depth += 1
                elif text[i] == close_ch:
                    depth -= 1
                    if depth == 0:
                        return text[start_idx : i + 1]
        return None

    def _complete_truncated_json(self, text: str) -> str:
        """If a JSON string appears truncated (unbalanced braces), try to close it.

        This is a best-effort heuristic and may not always succeed.
        """
        if not text:
            return text
        # count braces
        open_curly = text.count("{")
        close_curly = text.count("}")
        open_sq = text.count("[")
        close_sq = text.count("]")

        missing_curly = max(0, open_curly - close_curly)
        missing_sq = max(0, open_sq - close_sq)

        return text + ("}" * missing_curly) + ("]" * missing_sq)

    def _parse_ai_response(self, ai_text: Union[str, dict, list]) -> Union[dict, list]:
        """Robustly parse AI response into a Python object (dict or list).

        Tries multiple strategies to recover from truncated or wrapped outputs.
        """
        # If the model already returned a python structure, pass-through
        if isinstance(ai_text, (dict, list)):
            return ai_text

        # Ensure we have a string
        if not isinstance(ai_text, str):
            raise ValueError("AI response is not a string")

        def _default_cleanup(text: str) -> str:
            text = text.replace("\n", " ")
            text = text.replace("'", '"')
            text = text.replace(",}", "}").replace(",]", "]")
            return text

        ai_text_copy = ai_text.strip()
        ai_text_copy = _default_cleanup(ai_text_copy)

        # quick direct parse
        try:
            return json.loads(ai_text_copy)
        except Exception:
            pass

        # try to extract a JSON substring
        candidate = self._extract_json_substring(ai_text_copy)
        if candidate:
            try:
                candidate = _default_cleanup(candidate)
                return json.loads(candidate)
            except Exception:
                # try to auto-complete truncated JSON
                completed = self._complete_truncated_json(candidate)
                completed = _default_cleanup(completed)
                try:
                    return json.loads(completed)
                except Exception:
                    pass

        raise ValueError(f"Unable to parse AI response as JSON. Raw: {ai_text}")
