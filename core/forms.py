from django import forms


class FileUploadForm(forms.Form):
    """
    ファイルアップロードフォーム
    問題生成用の画像またはPDFファイルをアップロードするためのフォーム
    """
    file = forms.FileField(
        required=True,
        label="ファイル",
        widget=forms.FileInput(attrs={
            'accept': 'image/*,application/pdf',
            'class': 'file-input'
        })
    )