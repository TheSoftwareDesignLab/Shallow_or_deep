import warnings

from keras.backend import clear_session
from keras.layers import Dense
from keras.layers import Flatten
from keras.models import Sequential
from keras.optimizers import RMSprop
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation
from keras.optimizers import RMSprop
import numpy as np
import pandas as pd
import os
from keras.utils import np_utils
import joblib
from keras.preprocessing import sequence
from keras.optimizers import Adam
from keras.layers import GlobalMaxPooling1D, Embedding, LSTM
import pickle
from keras.models import load_model

import optuna
#number of epochs needed for training
EPOCHS= 100
#Length of the vocabulary per each approach, dataset and representation
# eg for binary, Russell, b0 is 150
VOCAB= 150
#Approach it can be binary 
approach = 'binary'
# Dataset Russell (R-DS), Juliet (J-DS) and OUR (GH-DS),
dataset= 'Russell'
# Representation b0 (R0), b1 (R1), b1_int (R2), b1_iden (R3), b1_int_iden (R4)
rep= 'b0'
# The path where the folder of the data (X and Y) is located
base_path= ''
#Model RNN
NN= 'RNN'

def objective(trial):
    # Clear clutter from previous Keras session graphs.
    clear_session()

    X_train = np.load(os.path.join(base_path,'Sequence_tokens',f'{approach}_{dataset}_train_{rep}.npy'))
    X_test = np.load(os.path.join(base_path,'Sequence_tokens',f'{approach}_{dataset}_val_{rep}.npy'))

    if approach == 'binary':
        df_Y_train = pd.read_csv(os.path.join(base_path,'Data_train_test',f'{approach}_Ytrain_{dataset}_{rep}.csv'))
        df_Y_train['VULN_N'] = df_Y_train['VULN_N'].apply(lambda x: 1 if x=='VULN' else 0)
        Y_train = df_Y_train['VULN_N']
        df_Y_test = pd.read_csv(os.path.join(base_path,'Data_train_test',f'{approach}_Yval_{dataset}_{rep}.csv'))
        df_Y_test['VULN_N'] = df_Y_test['VULN_N'].apply(lambda x: 1 if x=='VULN' else 0)
        Y_test = df_Y_test['VULN_N']

    vocab_size = VOCAB
    model = Sequential() 
    model.add(Embedding(input_dim = vocab_size, output_dim= trial.suggest_categorical("out_put", [8,16,32,64,128]), input_length=X_train.shape[1]))
    number_layers = trial.suggest_categorical("num_layers", [1,2])

    if number_layers ==2:
        units1 = trial.suggest_categorical("lstm_n1_units", [16,32,64,128])
        model.add(LSTM(units= units1,activation= trial.suggest_categorical("activation_lstm1",['tanh','relu','sigmoid']),
        return_sequences=True, kernel_initializer= trial.suggest_categorical("kernel_lstm1",['Orthogonal','lecun_uniform','he_normal']), 
        recurrent_initializer=trial.suggest_categorical("recurrent_lstm1",['glorot_normal','glorot_uniform'])))
        
        list_2 = []
        for i in [8,16,32,64,128]:
            if i < units1:
                list_2.append(i)

        units2 = trial.suggest_categorical(f"lstm_n2_units{list_2}", list_2)

        model.add(LSTM(units= units2,activation= trial.suggest_categorical("activation_lstm1",['tanh','relu','sigmoid']),
        return_sequences=False, kernel_initializer= trial.suggest_categorical("kernel_lstm2",['Orthogonal','lecun_uniform','he_normal']), 
        recurrent_initializer=trial.suggest_categorical("recurrent_lstm2",['glorot_normal','glorot_uniform'])))
    else:
        units1 = trial.suggest_categorical("lstm_n1_units", [16,32,64,128])
        model.add(LSTM(units= units1,activation= trial.suggest_categorical("activation_lstm1",['tanh','relu','sigmoid']),
        return_sequences=False, kernel_initializer= trial.suggest_categorical("kernel_lstm1",['Orthogonal','lecun_uniform','he_normal']), 
        recurrent_initializer=trial.suggest_categorical("recurrent_lstm1",['glorot_normal','glorot_uniform'])))

    
    if trial.suggest_categorical("drop_out_layer",[True,False]):
        model.add(Dropout(trial.suggest_categorical("drop_amount", [0.25,0.5])))


    dense_layers = trial.suggest_categorical("n_dense_layers", [0,1,2])

    if dense_layers == 2:
        model.add(Dense(8,activation= trial.suggest_categorical("act_1d_layer", ['relu','tanh'])))# applies to all

    if dense_layers==2 or dense_layers==1:
        model.add(Dense(6,activation= trial.suggest_categorical("act_2d_layer", ['relu','tanh'])))# applies to all


    #   sigmoid for binary
    model.add(Dense(1,activation='sigmoid'))
    model.compile(loss='binary_crossentropy',
                  optimizer=Adam(lr=trial.suggest_loguniform('learning_rate', 1e-4, 1e-2)),
                  metrics=['accuracy'])


    #Numero de epocas
    model.fit(X_train, Y_train,
              batch_size=trial.suggest_categorical("batch_size", [128,256,512]),
              nb_epoch=EPOCHS,
              verbose=2,
              validation_data=(X_test, Y_test))

    # Evaluate the model accuracy on the validation set.
    score = model.evaluate(X_test, Y_test, verbose=2)

    with open('{}_{}.h5'.format(rep,trial.number), 'wb') as fout:
        pickle.dump(model, fout)

    name_m= '{}_{}.h5'.format(rep,trial.number)
    model.save(name_m)

    return score[1]

if __name__ == "__main__":
    warnings.warn(
        "Recent Keras release (2.4.0) simply redirects all APIs "
        "in the standalone keras package to point to tf.keras. "
    )

    study_name = '{}_{}_{}_{}'.format(NN, approach, dataset, rep) # Unique identifier of the study.

    study = optuna.create_study(load_if_exists= True,direction="maximize", study_name=study_name, storage='sqlite:///{}_{}_{}_{}.db'.format(NN, approach, dataset, rep))
    study.optimize(objective, n_trials=25)

    print("Number of finished trials: {}".format(len(study.trials)))

    print("Best trial:")
    trial = study.best_trial

    print("  Value: {}".format(trial.value))

    print("  Params: ")
    for key, value in trial.params.items():
        print("    {}: {}".format(key, value))
