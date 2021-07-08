import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

import torchmetrics as tm
from nnAudio import Spectrogram

from models import BaseCatModel

from transformers import BertTokenizer, BertModel

class ACL1DConvCat_V1(BaseCatModel):

    
    ADAPTIVE_LAYER_UNITS = "adaptive_layer_units"
    N_FFT = "n_fft"
    N_MELS = "n_mels"
    N_MFCC = "n_mfcc"
    N_CQT = "n_cqt"
    SPEC_TRAINABLE = "spec_trainable"

    def __init__(self,
                batch_size=32,
                num_workers=4,
                train_ds=None,
                val_ds=None,
                test_ds=None,
                **model_config):
        super().__init__(batch_size, num_workers, train_ds, val_ds, test_ds, **model_config)

        self.__build_model()
    
    def __build_model(self):

        self.bert_tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        self.bert_model = BertModel.from_pretrained('bert-base-uncased', output_hidden_states=True)

        f_bins = (self.config[self.N_FFT] // 2) + 1

        self.stft = Spectrogram.STFT(n_fft=self.config[self.N_FFT], fmax=9000, sr=22050, trainable=self.config[self.SPEC_TRAINABLE], output_format="Magnitude")
        self.mel_spec = Spectrogram.MelSpectrogram(sr=22050, n_fft=self.config[self.N_FFT], n_mels=self.config[self.N_MELS], trainable_mel=self.config[self.SPEC_TRAINABLE], trainable_STFT=self.config[self.SPEC_TRAINABLE])
        self.mfcc = Spectrogram.MFCC(sr=22050, n_mfcc=self.config[self.N_MFCC])
        self.cqt = Spectrogram.CQT2010v2(sr=22050, hop_length=512, fmin=32.7, fmax=None, n_bins=self.config[self.N_CQT], filter_scale=1, bins_per_octave=12, norm=True, basis_norm=1, window='hann', pad_mode='reflect', earlydownsample=True, trainable=self.config[self.SPEC_TRAINABLE], output_format='Magnitude')

        self.audio_feature_extractor = nn.Sequential(
            nn.Conv1d(in_channels=1, out_channels=250, kernel_size=1024, stride=256),
            nn.BatchNorm1d(250),
            nn.Dropout(p=self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv1d(in_channels=250, out_channels=250, kernel_size=13, stride=5),
            nn.BatchNorm1d(250),
            nn.Dropout(p=self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv1d(in_channels=250, out_channels=250, kernel_size=13, stride=5),
            nn.BatchNorm1d(250),
            nn.Dropout(p=self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv1d(in_channels=250, out_channels=250, kernel_size=13, stride=5),
            nn.BatchNorm1d(250),
            nn.Dropout(p=self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.AdaptiveAvgPool1d(output_size=self.config[self.ADAPTIVE_LAYER_UNITS]),
            nn.Dropout()
        )

        self.stft_feature_extractor = nn.Sequential(

            nn.Conv1d(in_channels=f_bins, out_channels=500, kernel_size=3, stride=1),
            nn.MaxPool1d(kernel_size=2),
            nn.BatchNorm1d(num_features=500),
            nn.ReLU(),

            nn.Conv1d(in_channels=500, out_channels=500, kernel_size=3, stride=1),
            nn.MaxPool1d(kernel_size=2),
            nn.BatchNorm1d(num_features=500),
            nn.ReLU(),

            nn.Conv1d(in_channels=500, out_channels=500, kernel_size=3, stride=1),
            nn.MaxPool1d(kernel_size=2),
            nn.BatchNorm1d(num_features=500),
            nn.ReLU(),

            nn.AdaptiveAvgPool1d(output_size=self.config[self.ADAPTIVE_LAYER_UNITS])
        )

        self.mel_spec_feature_extractor = nn.Sequential(

            nn.Conv1d(in_channels=self.config[self.N_MELS], out_channels=100, kernel_size=3, stride=1),
            nn.MaxPool1d(kernel_size=2),
            nn.BatchNorm1d(num_features=100),
            nn.ReLU(),

            nn.Conv1d(in_channels=100, out_channels=100, kernel_size=3, stride=1),
            nn.MaxPool1d(kernel_size=2),
            nn.BatchNorm1d(num_features=100),
            nn.ReLU(),

            nn.AdaptiveAvgPool1d(output_size=self.config[self.ADAPTIVE_LAYER_UNITS])
        )

        self.mfcc_feature_extractor = nn.Sequential(

            nn.Conv1d(in_channels=self.config[self.N_MFCC], out_channels=16, kernel_size=3, stride=1),
            nn.MaxPool1d(kernel_size=2),
            nn.BatchNorm1d(num_features=16),
            nn.ReLU(),

            nn.Conv1d(in_channels=16, out_channels=16, kernel_size=3, stride=1),
            nn.MaxPool1d(kernel_size=2),
            nn.BatchNorm1d(num_features=16),
            nn.ReLU(),

            nn.Conv1d(in_channels=16, out_channels=16, kernel_size=3, stride=1),
            nn.MaxPool1d(kernel_size=2),
            nn.BatchNorm1d(num_features=16),
            nn.ReLU(),

            nn.AdaptiveAvgPool1d(output_size=self.config[self.ADAPTIVE_LAYER_UNITS])
        )

        self.cqt_feature_extractor = nn.Sequential(

            nn.Conv1d(in_channels=self.config[self.N_CQT], out_channels=100, kernel_size=3, stride=1),
            nn.MaxPool1d(kernel_size=2),
            nn.BatchNorm1d(num_features=100),
            nn.ReLU(),

            nn.Conv1d(in_channels=100, out_channels=100, kernel_size=3, stride=1),
            nn.MaxPool1d(kernel_size=2),
            nn.BatchNorm1d(num_features=100),
            nn.ReLU(),

            nn.Conv1d(in_channels=100, out_channels=100, kernel_size=3, stride=1),
            nn.MaxPool1d(kernel_size=2),
            nn.BatchNorm1d(num_features=100),
            nn.ReLU(),

            nn.AdaptiveAvgPool1d(output_size=self.config[self.ADAPTIVE_LAYER_UNITS])

        )

        self.lyrics_extractor = nn.LSTM(input_size=768, hidden_size=250, num_layers=1)

        out_channels = 250
        input_size = (self.config[self.ADAPTIVE_LAYER_UNITS] * out_channels)

        out_channels = 500
        input_size += (self.config[self.ADAPTIVE_LAYER_UNITS] * out_channels)

        out_channels = 100
        input_size += (self.config[self.ADAPTIVE_LAYER_UNITS] * out_channels)

        out_channels = 16
        input_size += (self.config[self.ADAPTIVE_LAYER_UNITS] * out_channels)

        out_channels = 100
        input_size += (self.config[self.ADAPTIVE_LAYER_UNITS] * out_channels)

        input_size += 250

        self.fc = nn.Sequential(
            nn.Linear(in_features=input_size, out_features=512),
            nn.ReLU(),
            nn.Dropout(p=self.config[self.DROPOUT]),
            nn.Linear(in_features=512, out_features=128),
            nn.ReLU(),
            nn.Linear(in_features=128, out_features=4)
        )

    def forward(self, x):

        (audio_x, lyrics_x) = x

        raw_x = self.audio_feature_extractor(audio_x)

        stft_x = self.stft(audio_x)
        stft_x = self.stft_feature_extractor(stft_x)

        mel_x = self.mel_spec(audio_x)
        mel_x = self.mel_spec_feature_extractor(mel_x)

        mfcc_x = self.mfcc(audio_x)
        mfcc_x = self.mfcc_feature_extractor(mfcc_x)

        cqt_x = self.cqt(audio_x)
        cqt_x = self.cqt_feature_extractor(cqt_x)

        lyrics_x = self.bert_tokenizer(lyrics_x, padding=True, truncation=False, return_tensors="pt", return_token_type_ids=False, return_attention_mask=False)['input_ids']
        with torch.no_grad():
            lyrics_x = self.bert_model(lyrics_x)
        lyrics_x = lyrics_x[0]
        (lyrics_x, _) = self.lyrics_extractor(lyrics_x)
        lyrics_x = lyrics_x[:, -1, :]

        raw_x = torch.flatten(raw_x, start_dim=1)
        stft_x = torch.flatten(stft_x, start_dim=1)
        mel_x = torch.flatten(mel_x, start_dim=1)
        mfcc_x = torch.flatten(mfcc_x, start_dim=1)
        cqt_x = torch.flatten(cqt_x, start_dim=1)
        lyrics_x = torch.flatten(lyrics_x, start_dim=1)

        x = torch.cat((raw_x, stft_x, mel_x, mfcc_x, cqt_x, lyrics_x), dim=1)

        x = self.fc(x)
        return x
