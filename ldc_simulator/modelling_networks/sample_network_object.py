import numpy as np



class Network(object):
    def __init__(self, n_params, n_class):
        # add weights for input layer, initialized randomly
        ratio = np.max([n_class / n_params, 1])
        self.weights = [2*np.random.random((n_params,n_params)) - 1]

        # add weights for hidden layer, initialized randomly
        # note: there are n_params hidden layers with 2*n_params nodes each
        for i in range(int(n_params/2)):
            col = n_params
            row = n_params
            self.weights.append(2*np.random.random((col,row)) - 1)

        # add weights for the output layer, initialized randomly
        self.weights.append(2*np.random.random((n_params,n_class)) - 1)
        
        for w in self.weights:
            print(w.shape)

        # Layer activations
        self.L = []
        
        # initial error
        self.error = [n_class]
        self.lr = 0.01
        
    # activators
    @staticmethod
    def sigmoid(x, derivative=False):
        if derivative: 
            return x*(1-x)
        else:
            return 1/(1+np.exp(-x))
    
    @staticmethod
    def tanh(x, derivative=False):
        if derivative: 
            return 1-(x**2)
        else:
            return (2/(1+np.exp(-2*x))) - 1

    @staticmethod
    def crossEntropy(predicted, target, derivative=False):
        """Return the cost associated with the 'predicted' and 'target' output.  
        Note: that np.nan_to_num is used to ensure numerical
        stability.  In particular, if both 'predicted' and 'target' have a 1.0
        in the same slot, then the expression (1-target)*np.log(1-predicted)
        returns nan.  The np.nan_to_num ensures that nan is converted
        to the correct value (0.0).
        """
        if derivative:
            return np.nan_to_num((-1) * ((target * (1/predicted)) - ((1-target) * (1/(1-predicted)))))
        else:
            return np.nan_to_num((-target*np.log(predicted)) - ((1-target)*np.log(1-predicted)))

    @staticmethod
    def get_accuracy(predicted,target):
        """Calculate the accuracy of the prediction
        """
    
        results = [(np.argmax(p), np.argmax(y))
                   for p, y in zip(predicted,target)]

        result_accuracy = sum(int(p == y) for (p, y) in results) / len(results)

        return result_accuracy


    
    # def get_accuracy(self,x_test,y_test):
    #     """Calculate the accuracy of the prediction
    #     """

    #     results = [(np.argmax(self.forwardProp(x)), np.argmax(y))
    #                    for (x, y) in zip(x_test,y_test)]
                       
     
    #     result_accuracy = sum(int(p == y) for (p, y) in results) / len(results)

    #     return result_accuracy


    # forward prop
    def forwardProp(self,x):
        self.L = []
        self.L.append(x)
        for w in self.weights:
            self.L.append(self.sigmoid(np.dot(self.L[-1], w)))

        return self.L[-1]

    # backward propagation/ gradient descent
    def backProp(self,error):
        G = [np.zeros(w.shape) for w in self.weights]
        L = self.L

        # compute error
        E = error
        
        for i in range(0,len(self.weights)):
            # calculate the weight delta of the current layer
            G[-(1+i)] = E*self.sigmoid(L[-(1+i)], derivative=True)

            # calculate the error for the next layer backwards
            E = G[-(1+i)].dot(self.weights[-(1+i)].T)

            # update weights
            self.weights[-(1+i)] -= L[-(2+i)].T.dot(G[-(1+i)]) * self.lr
            
            
        return G
    
    
    # train the model
    def train(self,x,y,n_epoch=60000, lr=0.01, report=1):
        self.lr = lr
        previousME = 9e9
        for i in range(n_epoch):
            # make predictions
            P = self.forwardProp(x)

            # calculate error
            error = self.crossEntropy(predicted=P, target=y)
            d_error = self.crossEntropy(predicted=P, target=y, derivative=True) # y - P

            
            # compute gradient and update weights
            G = self.backProp(d_error)
            

            # feedback prediction error
            if (i%report==0):
                accuracy = self.get_accuracy(P,y)

                # accuracy = self.get_accuracy(x,y_)
                print("Error: ", str(np.sum(np.abs(error))), "Accuracy: ", accuracy, "learning_rate: ", lr)
                # print('predicted:', P[0], 'expected:', y[0])
                
                currentME = np.mean([previousME,np.sum(np.abs(error))])
                if currentME >= previousME: lr = lr*0.1
                previousME = currentME
                
        return error, accuracy
            
            


#---TESTS---

# x = np.array([[0,0,0,0],
#              [0,0,0,1],
#              [0,0,1,0],
#              [0,0,1,1],
#              [0,1,0,0],
#              [0,1,0,1],
#              [0,1,1,0],
#              [0,1,1,1],])



# y = np.array([[1,0,0,0,0,0,0,0],
#              [0,1,0,0,0,0,0,0],
#              [0,0,1,0,0,0,0,0],
#              [0,0,0,1,0,0,0,0],
#              [0,0,0,0,1,0,0,0],
#              [0,0,0,0,0,1,0,0],
#              [0,0,0,0,0,0,1,0],
#              [0,0,0,0,0,0,0,1],])


x = np.random.randint(0, 10, 1000)
x = x.reshape((len(x), 1))

print(x)
y = np.sin(x)


print("Input shape:", x.shape, "Output shape:", y.shape)

N = Network(x.shape[1],y.shape[1])
            

# training in random order            
for j in range(20000):
    i = np.random.randint(0,len(x))
    x_train = x[i:].reshape(x.shape[0]-i,x.shape[1])
    y_train = y[i:].reshape(y.shape[0]-i,y.shape[1])
    N.train(x_train,y_train, n_epoch=10, lr=0.1)
