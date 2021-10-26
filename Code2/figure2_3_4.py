# -*- coding: utf-8 -*-
"""figure2-3-4.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1m-viV5uqBTGQ4mIzBKnr5dKw5M3HoI6r

Data PreProcessing
"""

# Commented out IPython magic to ensure Python compatibility.
# Data extraxtion and generating one hot vectores are done using the following reposetry
# https://github.com/itdxer/adult-dataset-analysis/blob/master/Classification.ipynb
import os
import sys

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# %matplotlib inline

prop_cycle = plt.rcParams['axes.prop_cycle']
colors = prop_cycle.by_key()['color']

CURRENT_DIR = os.path.abspath(os.path.dirname(__name__))
DATA_DIR = os.path.join('data')
TRAIN_DATA_FILE = os.path.join( 'adult.data')
TEST_DATA_FILE = os.path.join('adult.test')

from collections import OrderedDict

data_types = OrderedDict([
    ("age", "int"),
    ("workclass", "category"),
    ("final_weight", "int"),  # originally it was called fnlwgt
    ("education", "category"),
    ("education_num", "int"),
    ("marital_status", "category"),
    ("occupation", "category"),
    ("relationship", "category"),
    ("race", "category"),
    ("sex", "category"),
    ("capital_gain", "float"),  # required because of NaN values
    ("capital_loss", "int"),
    ("hours_per_week", "int"),
    ("native_country", "category"),
    ("income_class", "category"),
])
target_column = "income_class"

def read_dataset(path):
    return pd.read_csv(
        path,
        names=data_types,
        index_col=None,

        comment='|',  # test dataset has comment in it
        skipinitialspace=True,  # Skip spaces after delimiter
        na_values={
            'capital_gain': 99999,
            'workclass': '?',
            'native_country': '?',
            'occupation': '?',
        },
        dtype=data_types,
    )

def clean_dataset(data):
    # Test dataset has dot at the end, we remove it in order
    # to unify names between training and test datasets.
    data['income_class'] = data.income_class.str.rstrip('.').astype('category')
    
    # Remove final weight column since there is no use
    # for it during the classification.
    data = data.drop('final_weight', axis=1)
    
    # Duplicates might create biases during the analysis and
    # during prediction stage they might give over-optimistic
    # (or pessimistic) results.
    data = data.drop_duplicates()
    
    # Binarize target variable (>50K == 1 and <=50K == 0)
    data[target_column] = (data[target_column] == '>50K').astype(int)

    return data

def deduplicate(train_data, test_data):
    train_data['is_test'] = 0
    test_data['is_test'] = 1

    data = pd.concat([train_data, test_data])
    # For some reason concatenation converts this column to object
    data['native_country'] = data.native_country.astype('category')
    data = data.drop_duplicates()
    
    train_data = data[data.is_test == 0].drop('is_test', axis=1)
    test_data = data[data.is_test == 1].drop('is_test', axis=1)
    
    return train_data, test_data

train_data = clean_dataset(read_dataset(TRAIN_DATA_FILE))
test_data = clean_dataset(read_dataset(TEST_DATA_FILE))

# Note that we did de-duplication per dataset, but there are duplicates
# between training and test data. With duplicates between datasets
# we will might get overconfident results.
train_data, test_data = deduplicate(train_data, test_data)
print("Percent of the positive classes in the training data: {:.2%}".format(np.mean(train_data.income_class)))

def get_categorical_columns(data, cat_columns=None, fillna=True):
    if cat_columns is None:
        cat_data = data.select_dtypes('category')
    else:
        cat_data = data[cat_columns]

    if fillna:
        for colname, series in cat_data.iteritems():
            if 'Other' not in series.cat.categories:
                series = series.cat.add_categories(['Other'])

            cat_data[colname] = series.fillna('Other')
            
    return cat_data

def features_with_one_hot_encoded_categories(data, cat_columns=None, fillna=True):
    cat_data = get_categorical_columns(data, cat_columns, fillna)
    one_hot_data = pd.get_dummies(cat_data)
    df = pd.concat([data, one_hot_data], axis=1)

    features = [
        'age',
        'education_num',
        'hours_per_week',
        'capital_gain',
        'capital_loss',
    ] + one_hot_data.columns.tolist()
    features.remove('sex_Other')
    X = df[features].fillna(0).values.astype(float)
    y = df[target_column].values
    
    return X, y

"""Removing the datapoints that do not blong to the Black or White People"""

#Generating Training and Test data. column 65 coresponds to white race and column 63 coresponds to black race.  
X_train, y_train = features_with_one_hot_encoded_categories(train_data)
X_test, y_test = features_with_one_hot_encoded_categories(test_data)
y_train = y_train[((X_train[:,65]==1) | (X_train[:,63]==1)) ]
X_train = X_train[((X_train[:,65]==1) | (X_train[:,63]==1)),: ]
y_test = y_test[((X_test[:,65]==1) | (X_test[:,63]==1)) ]
X_test = X_test[((X_test[:,65]==1) | (X_test[:,63]==1)) , : ]
X_train = np.vstack((X_train,X_test))
y_train = np.concatenate([y_train,y_test])

"""Training a logistic regression classifier"""

from sklearn.linear_model import LogisticRegression
logisticRegr = LogisticRegression()
logisticRegr.fit(X_train, y_train)

"""Claculating $\Pr\{A\}$"""

p_black = sum(X_train[:,63]==1)/(sum(X_train[:,63]==1)+sum(X_train[:,65]==1))
p_white = 1-p_black

"""Next two blocks calculates $\Pr\{r(X,\tilde{a}) = \hat{y}, Y=1, A = a)\}$ for different values $\tilde{a}, \hat{y}$ and $a$"""

#now we generate two other datasets. The column 63 of X_train_all_black is all one. It assumes that all the datapoint comes from the black community

X_train_all_black = np.array(X_train)
X_train_all_black[:,63] = 1
X_train_all_black[:,65] = 0
X_train_all_white =np.array(X_train)
X_train_all_white[:,63] = 0
X_train_all_white[:,65] = 1

# calculating \Pr\{r(X,a)=y,Y = 1, A=a\} using training data, A=0 means white
predict = logisticRegr.predict(X_train_all_white)
Pr000 = sum((np.logical_and((predict == 0), np.logical_and((X_train[:,65]==1.0),y_train==1) )))/len(y_train)
Pr010 = sum((np.logical_and((predict == 1), np.logical_and((X_train[:,65]==1.0),y_train==1) )))/len(y_train)
Pr001 = sum((np.logical_and((predict == 0), np.logical_and((X_train[:,63]==1.0),y_train==1) )))/len(y_train)
Pr011 = sum((np.logical_and((predict == 1), np.logical_and((X_train[:,63]==1.0),y_train==1) )))/len(y_train)

predict = logisticRegr.predict(X_train_all_black)
Pr100 = sum((np.logical_and((predict == 0), np.logical_and((X_train[:,65]==1.0),y_train==1) )))/len(y_train)
Pr110 = sum((np.logical_and((predict == 1), np.logical_and((X_train[:,65]==1.0),y_train==1) )))/len(y_train)
Pr101 = sum((np.logical_and((predict == 0), np.logical_and((X_train[:,63]==1.0),y_train==1) )))/len(y_train)
Pr111 = sum((np.logical_and((predict == 1), np.logical_and((X_train[:,63]==1.0),y_train==1) )))/len(y_train)

"""Next  blocks calculates $\Pr\{r(X,\tilde{a}) = \hat{y}, A = a)\}$ for different values $\tilde{a}, \hat{y}$ and $a$"""

#calculating \Pr\{r(X,a)=y,A=a\} using training data 
#temp = np.array(X_train_all_white[((X_train[:,65]==1.0)),:])
#temp_y = np.array(y_train[((X_train[:,65]==1.0))])
#n = len(temp)
predict = logisticRegr.predict(X_train_all_white)
Pr000NoY = sum((np.logical_and((predict == 0), (X_train[:,65]==1.0) )))/len(y_train)
Pr010NoY = sum((np.logical_and((predict == 1), (X_train[:,65]==1.0) )))/len(y_train)
Pr001NoY = sum((np.logical_and((predict == 0), (X_train[:,63]==1.0) )))/len(y_train)
Pr011NoY = sum((np.logical_and((predict == 1), (X_train[:,63]==1.0) )))/len(y_train)

predict = logisticRegr.predict(X_train_all_black)
Pr100NoY = sum((np.logical_and((predict == 0), (X_train[:,65]==1.0) )))/len(y_train)
Pr110NoY = sum((np.logical_and((predict == 1), (X_train[:,65]==1.0) )))/len(y_train)
Pr101NoY = sum((np.logical_and((predict == 0), (X_train[:,63]==1.0) )))/len(y_train)
Pr111NoY = sum((np.logical_and((predict == 1), (X_train[:,63]==1.0) )))/len(y_train)

"""We solve optimization problem (9) under ES fairness notion"""

from scipy.optimize import linprog
o = []
beta = []
epsilon=np.linspace(0.01,7,100)
f0 = []
f1 = []
c = []
for e in epsilon:
  obj_coe = [-np.exp(e)*Pr000-Pr001,-np.exp(e)*Pr010-Pr011,-np.exp(e)*Pr101-Pr100,-np.exp(e)*Pr111-Pr110]
  condition1_coe = [np.exp(e)*Pr000 - Pr001  , np.exp(e)*Pr010 - Pr011,-np.exp(e)*Pr101 +  Pr100 , -np.exp(e)*Pr111 + Pr110  ]
  condition2_coe = [ np.exp(e)*Pr000NoY +  Pr001NoY   ,  np.exp(e)*Pr010NoY  +   Pr011NoY ,np.exp(e)*Pr101NoY  +  Pr100NoY  , np.exp(e)*Pr111NoY  + Pr110NoY]
  condition = [condition1_coe,condition2_coe]
  constant = [0,min([ np.exp(e)*Pr000NoY +  Pr001NoY   ,  np.exp(e)*Pr010NoY  +  Pr011NoY , np.exp(e)*Pr101NoY  +   Pr100NoY  ,  np.exp(e)*Pr111NoY  +   Pr110NoY])]
   
  bnd = [(0, 1), (0, 1), (0, 1) , (0, 1)]
  opt = linprog(c=obj_coe,A_eq=condition, b_eq=constant, bounds=bnd, method="revised simplex")
  o.append(-opt['x'].dot(obj_coe)/constant[1])
  f0.append(np.abs(np.array([np.exp(e)*Pr000  , np.exp(e)*Pr010,Pr100 , Pr110 ]).dot(opt['x'])/(   constant[1]      )) )
  f1.append(np.abs(np.array([Pr001  , Pr011, np.exp(e)*Pr101, np.exp(e)*Pr111  ]).dot(opt['x'])/(   constant[1]      )) )
  beta.append(opt['x'])
  c.append(condition1_coe)

"""We solve optimization problem (9) wihtout any fairness notion """

#solving optimization problem (14)
from scipy.optimize import linprog
o_nf = []
beta = []
epsilon=np.linspace(0.01,7,100)
f0_nf = []
f1_nf = []
c = []
for e in epsilon:
  obj_coe = [-np.exp(e)*Pr000-Pr001,-np.exp(e)*Pr010-Pr011,-np.exp(e)*Pr101-Pr100,-np.exp(e)*Pr111-Pr110]
  condition2_coe = [ np.exp(e)*Pr000NoY +  Pr001NoY   ,  np.exp(e)*Pr010NoY  +   Pr011NoY ,np.exp(e)*Pr101NoY  +  Pr100NoY  , np.exp(e)*Pr111NoY  + Pr110NoY]
  condition = [condition2_coe]
  constant = [min([ np.exp(e)*Pr000NoY +  Pr001NoY   ,  np.exp(e)*Pr010NoY  +  Pr011NoY , np.exp(e)*Pr101NoY  +   Pr100NoY  ,  np.exp(e)*Pr111NoY  +   Pr110NoY])]
   
  bnd = [(0, 1), (0, 1), (0, 1) , (0, 1)]
  opt = linprog(c=obj_coe,A_eq=condition, b_eq=constant, bounds=bnd, method="revised simplex")
  o_nf.append(-opt['x'].dot(obj_coe)/constant[0])
  f0_nf.append(np.abs(np.array([np.exp(e)*Pr000  , np.exp(e)*Pr010,Pr100 , Pr110 ]).dot(opt['x'])/(   constant[0]      )) )
  f1_nf.append(np.abs(np.array([Pr001  , Pr011, np.exp(e)*Pr101, np.exp(e)*Pr111  ]).dot(opt['x'])/(   constant[0]      )) )
  beta.append(opt['x'])
  c.append(condition1_coe)

"""We will solve optimization problem (9) under EO fairness notion.
In order to do that, we need to find $\Pr\{Y=1,A=a,R=y\}$ for different values of $a$ and $y$
"""

#effect of equal opportunity
predict = logisticRegr.predict(X_train)
temp = np.logical_and((X_train[:,65]==1.0),y_train==1)
temp = np.logical_and(temp,predict==1)
n = X_train.shape[0]
PrY1A0R1 = np.sum(temp)/n
###
predict = logisticRegr.predict(X_train)
temp = np.logical_and((X_train[:,63]==1.0),y_train==1)
temp = np.logical_and(temp,predict==1)
n = X_train.shape[0]
PrY1A1R1 = np.sum(temp)/n
###
predict = logisticRegr.predict(X_train)
temp = np.logical_and((X_train[:,65]==1.0),y_train==1)
temp = np.logical_and(temp,predict==0)
n = X_train.shape[0]
PrY1A0R0 = np.sum(temp)/n
###
predict = logisticRegr.predict(X_train)
temp = np.logical_and((X_train[:,63]==1.0),y_train==1)
temp = np.logical_and(temp,predict==0)
n = X_train.shape[0]
PrY1A1R0 = np.sum(temp)/n

"""We will solve optimization problem (9) under EO fairness notion.
In order to do that, we need to find $ \Pr (X,\tilde{a}) = y| Y=1,A=a)$ for different values of $\tilde{a},a$ and $y$
"""

#effect of equal opportunity \Pr r(X,tilde{a}) = y| Y=1,A=a)
temp = X_train_all_white[np.logical_and((X_train[:,65]==1.0),y_train==1)]
n = temp.shape[0]
PrAtild0R1_A0Y1 = np.sum(logisticRegr.predict(temp)==1)/n
PrAtild0R0_A0Y1 = np.sum(logisticRegr.predict(temp)==0)/n

temp = X_train_all_black[np.logical_and((X_train[:,65]==1.0),y_train==1)]
n = temp.shape[0]
PrAtild1R1_A0Y1 = np.sum(logisticRegr.predict(temp)==1)/n
PrAtild1R0_A0Y1 = np.sum(logisticRegr.predict(temp)==0)/n


temp = X_train_all_white[np.logical_and((X_train[:,63]==1.0),y_train==1)]
n = temp.shape[0]
PrAtild0R1_A1Y1 = np.sum(logisticRegr.predict(temp)==1)/n
PrAtild0R0_A1Y1 = np.sum(logisticRegr.predict(temp)==0)/n

temp = X_train_all_black[np.logical_and((X_train[:,63]==1.0),y_train==1)]
n = temp.shape[0]
PrAtild1R1_A1Y1 = np.sum(logisticRegr.predict(temp)==1)/n
PrAtild1R0_A1Y1 = np.sum(logisticRegr.predict(temp)==0)/n

"""We will solve optimization problem (9) under EO fairness notion.
In order to do that, we need to find $ \Pr ( R=y,A=a)$ for different values of $ a$ and $y$
"""

#effect of equal opportunity
predict = logisticRegr.predict(X_train)
temp = np.logical_and((X_train[:,65]==1.0),predict==1)
n = X_train.shape[0]
PrA0R1 = np.sum(temp)/n
###
predict = logisticRegr.predict(X_train)
temp = np.logical_and((X_train[:,63]==1.0),predict==1)
n = X_train.shape[0]
PrA1R1 = np.sum(temp)/n
###
predict = logisticRegr.predict(X_train)
temp = np.logical_and((X_train[:,65]==1.0),predict==0)
n = X_train.shape[0]
PrA0R0 = np.sum(temp)/n
###
predict = logisticRegr.predict(X_train)
temp = np.logical_and((X_train[:,63]==1.0),predict==0)
n = X_train.shape[0]
PrA1R0 = np.sum(temp)/n

"""We  solve optimization problem (9) under EO fairness notion.

"""

#solving optimization problem (14)
from scipy.optimize import linprog
o_eq = []
beta = []
epsilon=np.linspace(0.01,7,100)
f0_eq = []
f1_eq = []
c = []
for e in epsilon:
  obj_coe = [-np.exp(e)*Pr000-Pr001,-np.exp(e)*Pr010-Pr011,-np.exp(e)*Pr101-Pr100,-np.exp(e)*Pr111-Pr110]
  condition1_coe = [np.exp(e)*PrAtild0R0_A0Y1 - PrAtild0R0_A1Y1  , np.exp(e)*PrAtild0R1_A0Y1 - PrAtild0R1_A1Y1  ,
                    -np.exp(e)*PrAtild1R0_A1Y1 + PrAtild1R0_A0Y1 , -np.exp(e)*PrAtild1R1_A1Y1 + PrAtild1R1_A0Y1 ]
  condition2_coe = [ np.exp(e)*Pr000NoY +  Pr001NoY   ,  np.exp(e)*Pr010NoY  +   Pr011NoY ,np.exp(e)*Pr101NoY  +  Pr100NoY  , np.exp(e)*Pr111NoY  + Pr110NoY]
  condition = [condition1_coe,condition2_coe]
  constant = [0,min([ np.exp(e)*Pr000NoY +  Pr001NoY   ,  np.exp(e)*Pr010NoY  +  Pr011NoY , np.exp(e)*Pr101NoY  +   Pr100NoY  ,  np.exp(e)*Pr111NoY  +   Pr110NoY])]
   
  bnd = [(0, 1), (0, 1), (0, 1) , (0, 1)]
  opt = linprog(c=obj_coe,A_eq=condition, b_eq=constant, bounds=bnd, method="revised simplex")
  o_eq.append(-opt['x'].dot(obj_coe)/constant[1])
  f0_eq.append(np.abs(np.array([np.exp(e)*Pr000  , np.exp(e)*Pr010,Pr100 , Pr110 ]).dot(opt['x'])/(   constant[1]      )) )
  f1_eq.append(np.abs(np.array([Pr001  , Pr011, np.exp(e)*Pr101, np.exp(e)*Pr111  ]).dot(opt['x'])/(   constant[1]      )) )
  beta.append(opt['x'])
  c.append(condition1_coe)

"""We plot figure 2 3 4"""

font = {'family' : 'normal',
        'size'   : 15}
import matplotlib
matplotlib.rc('font', **font)
plt.figure(figsize=(5,4))
plt.plot(epsilon,o,'b',label=r'ES',linewidth=4)
plt.plot(epsilon,o_eq,'r',label=r'EO',linewidth=4)
plt.plot(epsilon,o_nf,'--g',label=r'None',linewidth=4)
plt.legend(loc='lower right' )
plt.xlabel(r'Privacy Loss $\epsilon$')
plt.ylabel(r'Accuracy')
plt.grid()
plt.savefig('acc.eps', format='eps',bbox_inches='tight')

plt.figure(figsize=(5,4))
l1, = plt.plot(epsilon,f0,'r',label=r'White: ES',linewidth=4)
l2, = plt.plot(epsilon,f1,'b:' ,label=r'Black: ES',linewidth=4)
l3, = plt.plot(epsilon,f0_eq*np.ones(epsilon.shape),'#C4DF76',label=r'White: EO',linewidth=4)
l4, = plt.plot(epsilon,f1_eq*np.ones(epsilon.shape),'c' ,label=r'Black: EO',linewidth=4)
l5, = plt.plot(epsilon,f0_nf,'g--',label=r'White: None',linewidth=4)
l6, = plt.plot(epsilon,f1_nf,'y--', label=r'Black: None',linewidth=4)

# Create a legend for the first line.
first_legend = plt.legend(handles=[l1,l2,l3], loc='upper right', bbox_to_anchor=(1, 0.9))

# Add the legend manually to the current Axes.
plt.gca().add_artist(first_legend)

# Create another legend for the second line.
plt.legend(handles=[l4,l5,l6], loc='lower right',bbox_to_anchor=(1,  0.1))

plt.xlabel(r'Privacy Loss $\epsilon$')
plt.ylabel(r'$\Pr\{E_a,\tilde{Y}=1\}$')
plt.grid()

plt.savefig('fair.eps', format='eps',bbox_inches='tight')


plt.figure(figsize=(5,4))
plt.plot(epsilon,abs(np.array(f0)-np.array(f1)),'r',label=r'ES',linewidth=4)
plt.plot(epsilon,abs(np.array(f0_eq)-np.array(f1_eq)),'#C4DF76',label=r'EO',linewidth=4)
plt.plot(epsilon,abs(np.array(f0_nf)-np.array(f1_nf)),'g--',label=r'None',linewidth=4)
plt.legend(loc='right')
plt.xlabel(r'Privacy Loss $\epsilon$')
plt.ylabel(r'disparity ($\gamma$)')

plt.grid()

plt.savefig('disparity.eps', format='eps',bbox_inches='tight')