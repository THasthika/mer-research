from utils.helpers import magic_combine
from models import BaseStatModel
import numpy as np
import pytorch_lightning as pl

import torch
import torch.nn as nn

from nnAudio import Spectrogram
from utils.activation import CustomELU
from utils.layer import Unsqueeze


class AC2DConvLSTMStat_V2(BaseStatModel):

    AUDIO_HIDDEN_SIZE = "audio_hidden_size"
    AUDIO_NUM_LAYERS = "audio_num_layers"

    STFT_HIDDEN_SIZE = "stft_hidden_size"
    STFT_NUM_LAYERS = "stft_num_layers"

    MEL_SPEC_HIDDEN_SIZE = "mel_spec_hidden_size"
    MEL_SPEC_NUM_LAYERS = "mel_spec_num_layers"

    MFCC_HIDDEN_SIZE = "mfcc_hidden_size"
    MFCC_NUM_LAYERS = "mfcc_num_layers"

    N_FFT = "n_fft"
    N_MELS = "n_mels"
    N_MFCC = "n_mfcc"
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

        self.audio_feature_extractor = nn.Sequential(
            nn.Conv1d(in_channels=1, out_channels=250, kernel_size=1024, stride=256),
            nn.BatchNorm1d(250),
            nn.Dropout(self.config[self.DROPOUT]),
            nn.ReLU(),

            Unsqueeze(1),

            nn.Conv2d(in_channels=1, out_channels=16, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(16),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(1, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=16, out_channels=32, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(32),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(1, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(64),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(1, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=64, out_channels=128, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(128),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(128),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(128),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(128),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 2)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(128),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 2)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU()
        )

        self.audio_lstm = nn.LSTM(
            input_size=128 * 4,
            hidden_size=self.config[self.AUDIO_HIDDEN_SIZE],
            num_layers=self.config[self.AUDIO_NUM_LAYERS]
        )

        self.stft_feature_extractor = nn.Sequential(
            Unsqueeze(1),

            nn.Conv2d(in_channels=1, out_channels=16, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(16),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(1, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=16, out_channels=32, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(32),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(64),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=64, out_channels=128, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(128),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(128),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(128),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 2)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(128),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 2)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU()
        )

        self.stft_lstm = nn.LSTM(
            input_size=128 * 5,
            hidden_size=self.config[self.STFT_HIDDEN_SIZE],
            num_layers=self.config[self.STFT_NUM_LAYERS]
        )

        self.mel_spec_feature_extractor = nn.Sequential(
            Unsqueeze(1),

            nn.Conv2d(in_channels=1, out_channels=16, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(16),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(1, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=16, out_channels=32, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(32),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(1, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(64),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=64, out_channels=128, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(128),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(128),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(128),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(2, 2)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU()
        )


        self.mel_spec_lstm = nn.LSTM(
            input_size=128 * 4,
            hidden_size=self.config[self.MEL_SPEC_HIDDEN_SIZE],
            num_layers=self.config[self.MEL_SPEC_NUM_LAYERS]
        )

        self.mfcc_feature_extractor = nn.Sequential(
            Unsqueeze(1),

            nn.Conv2d(in_channels=1, out_channels=16, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(16),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(1, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=16, out_channels=32, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(32),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(1, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(64),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(1, 1)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

            nn.Conv2d(in_channels=64, out_channels=128, kernel_size=(3, 3), stride=(1, 1)),
            nn.BatchNorm2d(128),
            nn.AvgPool2d(kernel_size=(3, 3), stride=(1, 2)),
            nn.Dropout2d(self.config[self.DROPOUT]),
            nn.ReLU(),

        )

        self.mfcc_lstm = nn.LSTM(
            input_size=128 * 4,
            hidden_size=self.config[self.MFCC_HIDDEN_SIZE],
            num_layers=self.config[self.MFCC_NUM_LAYERS]
        )

        input_size = self.config[self.AUDIO_HIDDEN_SIZE]
        input_size += self.config[self.STFT_HIDDEN_SIZE]
        input_size += self.config[self.MEL_SPEC_HIDDEN_SIZE]
        input_size += self.config[self.MFCC_HIDDEN_SIZE]

        self.fc = nn.Sequential(
            nn.Linear(in_features=input_size, out_features=512),
            nn.Dropout(p=self.config[self.DROPOUT]),
            nn.ReLU(),
            nn.Linear(in_features=512, out_features=128),
            nn.ReLU()
        )

        self.fc_mean = nn.Sequential(
            nn.Linear(in_features=128, out_features=2)
        )

        self.fc_std = nn.Sequential(
            nn.Linear(in_features=128, out_features=2),
            self._get_std_activation()
        )

    def forward(self, x):

        (audio_x, stft_x, mel_x, mfcc_x) = x

        print(audio_x.shape)
        print(stft_x.shape)
        print(mel_x.shape)
        print(mfcc_x.shape)

        audio_x = self.audio_feature_extractor(audio_x)
        stft_x = self.stft_feature_extractor(stft_x)
        mel_x = self.mel_spec_feature_extractor(mel_x)
        mfcc_x = self.mfcc_feature_extractor(mfcc_x)

        audio_x = magic_combine(audio_x, 1, 3)
        stft_x = magic_combine(stft_x, 1, 3)
        mel_x = magic_combine(mel_x, 1, 3)
        mfcc_x = magic_combine(mfcc_x, 1, 3)

        audio_x = audio_x.permute((0, 2, 1))
        stft_x = stft_x.permute((0, 2, 1))
        mel_x = mel_x.permute((0, 2, 1))
        mfcc_x = mfcc_x.permute((0, 2, 1))

        (out, _) = self.audio_lstm(audio_x)
        audio_x = out[:, -1, :]

        (out, _) = self.stft_lstm(stft_x)
        stft_x = out[:, -1, :]

        (out, _) = self.mel_spec_lstm(mel_x)
        mel_x = out[:, -1, :]

        (out, _) = self.mfcc_lstm(mfcc_x)
        mfcc_x = out[:, -1, :]

        x = torch.cat((audio_x, stft_x, mel_x, mfcc_x), dim=1)

        x = self.fc(x)
        x_mean = self.fc_mean(x)
        x_std = self.fc_std(x)
        x = torch.cat((x_mean, x_std), dim=1)
        return x
