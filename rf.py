"Scott's script for training a random forest on the 2006 and 2008 ADDM evaluations" 
import pandas as pd
import numpy as np
import sklearn
import argparse
from generic import *
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score, KFold

#performs a stepwise search for the optimal number of features in a trimmed random forest
def tune(model, min_features=1, max_features=200):
    out = pd.DataFrame(data=np.empty([max_features - min_features + 1, 2]), columns=['n_features', 'acc'])
    out['n_features'] =  range(min_features, max_features + 1)    
    for i in range(min_features, max_features + 1):
	all_ftrs = full_model.feature_importances_
	sort_ftrs = np.argsort(all_ftrs)[-i:]
	clf = RandomForestClassifier(n_estimators=n_estimators)
	clf = clf.fit(x_train[:, sort_ftrs], y_train)
	acc = clf.score(x_test[:, sort_ftrs], y_test)
	print "Number of features: %s" %i
	print "Model accuracy: %s \n" %acc
	out['acc'][i - min_features] = acc
    return out

#returns the top n features by importance in the TextRF
def print_top_features(model, n=10):
	print "\nThe top %i features are..." %n
	for x in xrange(n):
		print model.top_features[n]
	return

#main class for the text-based random forest; has methods for loading and processing data,
#as well as model-specific attributes like accuracy and feature names
class TextRF:
	def __init__(self, trees=1000):
		#setting attributes for the RF
		self.feature_names = []
		self.feature_importances = []
		self.trees = trees
		self.mod = []
		
		#setting attributes for the data
		self.X, self.y = [], []
		self.X_train, self.X_test = [], []
		self.y_train, self.y_test = [], []
	
	#main function for training and testing the random forest
	def fit(self, X, y, top=100, jobs=-1, verbose=False, prune=True):
		
		#passing the training data up to the instance
		self.X_train, self.y_train = X, y
		
		#training the RF on the docs
		if verbose:
			print "Training the random forest..."
		rf = RandomForestClassifier(n_estimators=self.trees, class_weight='balanced_subsample', n_jobs=jobs)
		mod = rf.fit(self.X_train, self.y_train)
		importances = mod.feature_importances_
			
		if prune:
			#trimming the tree to the top features
			sorted_indices = np.argsort(importances)
			trimmed_indices = np.array(sorted_indices[-top:])
			self.feature_indices = trimmed_indices
			
			#pruning the unnecessary features from the training data
			self.X_train = X[:, trimmed_indices]
			
			#training a new forest on the pruned data
			mod = RandomForestClassifier(n_estimators=self.trees, class_weight='balanced_subsample', n_jobs=jobs)
			mod.fit(self.X_train, self.y_train)
		
		#setting instance attributes using data from the trimmed model
		self.mod = mod
		self.feature_importances = importances
	
	#wrappers for the sklearn functions; admittedly redundant	
	def score(self, X, y):
		self.X_test = X[:, self.feature_indices]
		self.y_test = y
		return self.mod.score(self.X_test, y)

	def predict(self, X, y):
		self.X_test = X[:, self.feature_indices]
		return self.mod.predict(self.X_test)
 
	def predict_proba(self, X, y):
		self.X_test = X[:, self.feature_indices]
		return self.mod.predict_proba(self.X_test)		
			
#running an example of the model
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	
	#positional arguments
	parser.add_argument('data', help='data path for the corpus (in CSV format)')
	parser.add_argument('x_name', help='name of the column holding the text')
	parser.add_argument('y_name', help='name of the column holding the target variable')
	
	#optional arguments
	parser.add_argument('-lm', '--limit_features', default='yes', help='limit the number of features for the RF? (yes or no)')
	parser.add_argument('-ft', '--features', type=int, default=10000, help='number of features for the SVM, if limited')
	parser.add_argument('-vc', '--vec_meth', default='tfidf', help='method for vectorizing the text; count or tfidf')
	parser.add_argument('-tr', '--n_trees', type=int, default=1000, help='number of trees to use in the RF')
	parser.add_argument('-ng', '--ngrams', type=int, default=2, help='max ngram size')
	parser.add_argument('-sm', '--split_method', default='train-test', help='split the data by year, train-test, or cross-val')
	parser.add_argument('-sv', '--split_variable', default='year', help='variable to used for splitting the data')
	parser.add_argument('-yr', '--test_val', help='which value of split_variable to use for the test data')
	
	args = parser.parse_args()
	
	#loading the data and training the RF
	corpus = pd.read_csv(args.data)
	data = TextData()
	data.process(corpus, args.x_name, args.y_name, args.ngrams, args.features, args.vec_meth, args.limit_features)
	data.split(args.split_method, args.split_variable, args.test_val)
	
	#fitting the model and getting the statz	
	mod = TextRF(trees=args.n_trees)
	mod.fit(data.X_train, data.y_train)
	print "\nModel accuracy is %0.4f" %mod.score(data.X_test, data.y_test)

