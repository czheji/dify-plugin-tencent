import json
from typing import IO, Optional

import requests
from dify_plugin.errors.model import (CredentialsValidateFailedError,
                                      InvokeAuthorizationError,
                                      InvokeConnectionError, InvokeError)
from dify_plugin.interfaces.model.speech2text_model import Speech2TextModel

from .flash_recognizer import (Credential, FlashRecognitionRequest,
                               FlashRecognizer)


class TencentSpeech2TextModel(Speech2TextModel):
    def _invoke(self, model: str, credentials: dict, file: IO[bytes], user: Optional[str] = None) -> str:
        """
        Invoke speech2text model

        :param model: model name
        :param credentials: model credentials
        :param file: audio file
        :param user: unique user id
        :return: text for given audio file
        """
        return self._speech2text_invoke(model, credentials, file)

    def validate_credentials(self, model: str, credentials: dict) -> None:
        """
        Validate model credentials

        :param model: model name
        :param credentials: model credentials
        :return:
        """
        try:
            audio_file_path = self._get_demo_file_path()

            with open(audio_file_path, "rb") as audio_file:
                self._speech2text_invoke(model, credentials, audio_file)
        except Exception as ex:
            raise CredentialsValidateFailedError(str(ex))

    def _speech2text_invoke(self, model: str, credentials: dict, file: IO[bytes]) -> str:
        """
        Invoke speech2text model

        :param model: model name
        :param credentials: model credentials
        :param file: audio file
        :return: text for given audio file
        """
        app_id = credentials["app_id"]
        secret_id = credentials["secret_id"]
        secret_key = credentials["secret_key"]
        engine_type = credentials["engine_type"] if "engine_type" in credentials else "16k_zh_large"
        voice_format = credentials["voice_format"] if "voice_format" in credentials else "m4a"
        voice_format = file.voice_format if hasattr(file, "voice_format") else voice_format
        tencent_voice_recognizer = FlashRecognizer(app_id, Credential(secret_id, secret_key))
        resp = tencent_voice_recognizer.recognize(FlashRecognitionRequest(voice_format, engine_type), file)
        resp = json.loads(resp)
        code = resp["code"]
        message = resp["message"]
        if code == 4002:
            raise CredentialsValidateFailedError(str(message))
        elif code != 0:
            return f"Tencent ASR Recognition failed with code {code} and message {message}"
        return "\n".join(item["text"] for item in resp["flash_result"])

    @property
    def _invoke_error_mapping(self) -> dict[type[InvokeError], list[type[Exception]]]:
        """
        Map model invoke error to unified error
        The key is the error type thrown to the caller
        The value is the error type thrown by the model,
        which needs to be converted into a unified error type for the caller.

        :return: Invoke error mapping
        """
        return {
            InvokeConnectionError: [requests.exceptions.ConnectionError],
            InvokeAuthorizationError: [CredentialsValidateFailedError],
        }
