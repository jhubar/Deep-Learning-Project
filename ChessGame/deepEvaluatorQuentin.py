import argparse
import chess
import math
import statistics

import matplotlib.pyplot as plt

# for creating validation set
from sklearn.model_selection import train_test_split

# for evaluating the model
from sklearn.metrics import accuracy_score

import pickle

import numpy as np

import torch
from torch.nn import Linear, Sequential, ReLU, Conv2d, BatchNorm1d, BatchNorm2d, Module, MSELoss, ELU, Softmax, Dropout, DataParallel
from torch.nn.functional import elu, relu
from torch.nn.init import xavier_uniform_, zeros_, calculate_gain
from torch.optim import Adam, SGD
from torch.utils.data import TensorDataset, DataLoader
from torchvision.transforms import Compose, Normalize

from evaluator import Evaluator

#device = 'cuda' if torch.cuda.is_available() else 'cpu'
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
# device = 'cpu'
# print(device)

MODELPATH = "./deqModel.pth"


def weight_init(m):
    if isinstance(m, Conv2d) or isinstance(m, Linear):
        xavier_uniform_(m.weight, gain=calculate_gain('relu'))
        zeros_(m.bias)


class CustomNet(Module):
    def __init__(self):
        super(CustomNet, self).__init__()

        self.conv1 = Conv2d(12, 20, 5)
        self.conv2 = Conv2d(20, 50, 3)

        # self.fc1 = Linear(50 * 2 * 2, 1)
        self.fc1 = Linear(50 * 2 * 2, 500)
        self.fc2 = Linear(500, 1)
        self.fc3 = Linear(200, 1)

        self.bn1 = BatchNorm2d(20)
        self.bn2 = BatchNorm2d(50)
        self.bn3 = BatchNorm1d(500)

        self.drop = Dropout(0.3)

        # self.cnnModel = Sequential(
        #     # First layer
        #     Conv2d(12, 20, kernel_size=5, stride=1, padding=0),
        #     BatchNorm2d(20),
        #     Dropout(p=0.3),
        #     ELU(),
        #     # Second layer
        #     Conv2d(20, 50, kernel_size=3, stride=1, padding=0),
        #     BatchNorm2d(50),
        #     Dropout(p=0.3),
        #     ELU(),
        # )

        # self.fcModel = Sequential(
        #     Dropout(p=0.3),
        #     BatchNorm1d(200),
        #     Linear(200, 1),
        #     # Softmax(1),
        # )

    def forward(self, x):
        # xconv = self.cnnModel(x)
        # # xflat = xconv.flatten()
        # xflat = xconv.view(xconv.size(0), -1)
        # res = self.fcModel(xflat)
        res = elu(self.conv1(x))
        res = self.bn1(res)
        res = self.drop(res)

        res = elu(self.conv2(res))
        res = self.bn2(res)
        res = self.drop(res)

        # res = res.view(-1, 50 * 2 * 2)
        # res = res.view(50 * 2 *2, -1)
        res = res.view(-1, 50 * 2 *2)

        # res = elu(self.fc1(res))
        # res = self.fc2(res)

        res = self.fc3(res)
        # res = self.bn3(res)

        return res


class DeepEvaluator(Evaluator):
    def __init__(self, evalMode: bool):
        self.model = CustomNet().to(device)

        if evalMode:
            self.model.load_state_dict(torch.load(
                MODELPATH, map_location=torch.device('cpu')))
            self.model.eval()
        else:
        # if torch.cuda.device_count() > 1:
        #     print("Let's use", torch.cuda.device_count(), "GPUs!")
        #     # dim = 0 [30, xxx] -> [10, ...], [10, ...], [10, ...] on 3 GPUs
        #     self.model = DataParallel(self.model)
        # self.model = self.model.to(device)
        # self.model.apply(init_weights)
            self.model.apply(weight_init)

        # self.optimizer = Adam(self.model.parameters(), lr=0.07)
        self.criterion = MSELoss()
        self.optimizer = SGD(self.model.parameters(), lr=0.001)

        # defining the number of epochs
        self.n_epochs = 50
        # empty list to store training losses
        # self.train_losses = []
        # empty list to store validation losses
        # self.val_losses = []

    @staticmethod
    def boardToTensor(board):
        tensor = torch.zeros(12, 8, 8)

        for wp in board.pieces(chess.PAWN, chess.WHITE):
            row = wp // 8
            col = wp % 8
            tensor[0][row][col] = 1
        for wn in board.pieces(chess.KNIGHT, chess.WHITE):
            row = wn // 8
            col = wn % 8
            tensor[1][row][col] = 1
        for wb in board.pieces(chess.BISHOP, chess.WHITE):
            row = wb // 8
            col = wb % 8
            tensor[2][row][col] = 1
        for wr in board.pieces(chess.ROOK, chess.WHITE):
            row = wr // 8
            col = wr % 8
            tensor[3][row][col] = 1
        for wq in board.pieces(chess.QUEEN, chess.WHITE):
            row = wq // 8
            col = wq % 8
            tensor[4][row][col] = 1
        for wk in board.pieces(chess.KING, chess.WHITE):
            row = wk // 8
            col = wk % 8
            tensor[5][row][col] = 1
        for bp in board.pieces(chess.PAWN, chess.BLACK):
            row = bp // 8
            col = bp % 8
            tensor[6][row][col] = 1
        for bn in board.pieces(chess.KNIGHT, chess.BLACK):
            row = bn // 8
            col = bn % 8
            tensor[7][row][col] = 1
        for bb in board.pieces(chess.BISHOP, chess.BLACK):
            row = bb // 8
            col = bb % 8
            tensor[8][row][col] = 1
        for br in board.pieces(chess.ROOK, chess.BLACK):
            row = br // 8
            col = br % 8
            tensor[9][row][col] = 1
        for bq in board.pieces(chess.QUEEN, chess.BLACK):
            row = bq // 8
            col = bq % 8
            tensor[10][row][col] = 1
        for bk in board.pieces(chess.KING, chess.BLACK):
            row = bk // 8
            col = bk % 8
            tensor[11][row][col] = 1

        return tensor

    def evaluate(self, board: chess.Board):

        if board.turn is chess.BLACK:
            board = board.mirror()
        tensor = DeepEvaluator.boardToTensor(board)
        tensor = tensor.view(1, 12, 8, 8)

        output = self.model(tensor)
        # model.load_state_dict(torch.load(MODELPATH))
        # return model.eval(tensor)

        if board.turn is chess.BLACK:
            output = -output

        return output

    def loadDataset(self):
        with open("Data/chessInput-medium", "rb") as file:
            trainInput = pickle.load(file)

        with open("Data/chessOutput-medium", "rb") as file:
            trainOutput = pickle.load(file)

        # train_X, val_X, train_y, val_y = train_test_split(
        #     trainInput, trainOutput, test_size=0.1)

        train_X = torch.stack(trainInput)
        train_y = torch.FloatTensor(trainOutput)
        train_y = train_y.view(-1, 1)

        train_X.to(device)
        train_y.to(device)

        # train_y = (train_y - torch.mean(train_y)) / torch.std(train_y)

        # train_y = train_y/train_y.sum(0).expand_as(train_y)
        # train_y[torch.isnan(train_y)] = 0

        train_y -= torch.min(train_y)
        train_y /= torch.max(train_y)

        train_X = train_X
        train_y = train_y

        splitFactor = 0.9
        split = math.floor(len(train_X) * splitFactor)

        train_data = TensorDataset(train_X[:split], train_y[:split])
        test_data = TensorDataset(train_X[split:], train_y[split:])

        return train_data, test_data

    def train(self, train_X, train_y):
        # self.model.train()
        self.optimizer.zero_grad()

        # # getting the training set
        # X_train = Variable(train_X)
        # y_train = Variable(train_y)
        X_train = train_X
        y_train = train_y

        # prediction for training and validation set
        output_train = self.model(X_train)

        # computing the training and validation loss
        loss_train = self.criterion(output_train, y_train)

        # computing the updated weights of all the model parameters
        loss_train.backward()

        self.optimizer.step()

        return loss_train.item()


if __name__ == "__main__":
    evaluator = DeepEvaluator(False)

    train_data, test_data = evaluator.loadDataset()

    batch_size = 128
    # print 2 times per epoch
    # print_step = len(train_data) // batch_size // 2
    print_step = 20

    train_loader = DataLoader(
        dataset=train_data, batch_size=batch_size, shuffle=True, num_workers=2)

    test_loader = DataLoader(
        dataset=test_data, batch_size=batch_size, shuffle=False, num_workers=2)

    # X_batch, y_batch = next(iter(train_loader))
    # X_test, y_test = next(iter(train_loader))

    train_losses = []
    epoch_losses = []

    for epoch in range(evaluator.n_epochs):
        running_loss = 0.0
        tmp = []

        for i, data in enumerate(train_loader, 0):
            X_batch, y_batch = data
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            loss = evaluator.train(X_batch, y_batch)
            running_loss += loss
        # X_batch = X_batch.to(device)
        # y_batch = y_batch.to(device)
        # loss = evaluator.train(epoch, X_batch, y_batch)
            train_losses.append(loss)
            tmp.append(loss)

            if i % print_step == print_step - 1:
                # print("Epoch : {}\tBatch : {}\tLoss : {:.3f}".format(epoch+1, i+1, train_losses[-1]))
                print("Epoch : {}\tBatch : {}\tLoss : {:.3f}".format(
                    epoch+1, i+1, running_loss / print_step))
                # train_losses.append(running_loss / print_step)
                running_loss = 0.0

        epoch_losses.append(statistics.mean(tmp))

    epochs = np.arange(evaluator.n_epochs)
    mean_num_train = len(train_losses) / len(epochs)
    epochs = epochs * mean_num_train
    plt.plot(train_losses)
    plt.plot(epochs, epoch_losses)
    plt.savefig("Graph/deq_ds{}_bs{}_ne{}_ps{}_1".format(len(train_data),
                                                       batch_size, evaluator.n_epochs, print_step))
    # plt.show()

    mse = []
    outs = []
    truth = []
    mean = []
    with torch.no_grad():
        for data in test_loader:
            X, y = data
            X = X.to(device)
            y = y.to(device)
            y = y.view(-1, 1)
            mean.append(torch.mean(y).item())
            outputs = evaluator.model(X)
            outs.extend(outputs.cpu().numpy())
            truth.extend(y.cpu().numpy())
            mse.append(evaluator.criterion(outputs, y).item())

    print("Average mean square error of the network on the test set: {:.2%}, {}".format(
        statistics.mean(mse), statistics.mean(mse)))
    print("Ground truth : min = {}, max = {}, mean = {}".format(min(truth), max(truth), statistics.mean(mean)))
    plt.clf()
    plt.plot(outs)
    plt.plot(truth)
    plt.legend(['Outputs', 'Ground truth'], loc='upper right')
    plt.savefig("Graph/deq_ds{}_bs{}_ne{}_ps{}_2".format(len(train_data),
                                                         batch_size, evaluator.n_epochs, print_step))

    torch.save(evaluator.model.state_dict(), MODELPATH)
    # plt.show()
