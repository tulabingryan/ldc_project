import numpy as np


# x = np.array([[0,0,1],
#              [0,1,1],
#              [1,0,1],
#              [1,1,1]])


# y = np.array([[0],
#              [1],
#              [1],
#              [0]])

x = np.array([list(format(i, '010b')) for i in range(10)]).astype(int)
y = np.zeros((10, 10))
for i in range(10):
    y[i][i] = 1

# network model
# # initial weights
# W0 = 2*np.random.random((x.shape[1],4)) - 1
# W1 = 2*np.random.random((4,y.shape[1])) - 1


input_shape = x.shape
output_shape = y.shape
n_params = input_shape[1]
n_class = output_shape[1]



ratio = np.max([n_class / n_params, 1])
weights = [2*np.random.random((n_params,n_params)) - 1]

# add weights for hidden layer, initialized randomly
# note: there are n_params hidden layers with 2*n_params nodes each
for i in range(int(n_params/2)):
    col = n_params
    row = n_params
    weights.append(2*np.random.random((col,row)) - 1)

# add weights for the output layer, initialized randomly
weights.append(2*np.random.random((n_params,n_class)) - 1)

for w in weights:
    print(w.shape)

# Layer activations
L = []

# initial error
error = [n_class]
lr = 0.01


# # add weights for input layer, initialized randomly
# weights = [2*np.random.random((n_params,n_params*2)) - 1]

# # add weights for hidden layer, initialized randomly
# # note: there are n_params hidden layers with 2*n_params nodes each
# for i in range(n_params):
#     weights.append(2*np.random.random((n_params*2,n_params*2)) - 1)

# # add weights for the output layer, initialized randomly
# weights.append(2*np.random.random((n_params*2,n_class)) - 1)


# activators
def sigmoid(x, derivative=False):
    if derivative: 
        return x*(1-x)
    else:
        return 1/(1+np.exp(-x))
    

def tanh(x, derivative=False):
    if derivative: 
        return 1-(x**2)
    else:
        return (2/(1+np.exp(-2*x))) - 1
        
    



# forward prop
def forwardProp(x, weights):
    L = []
    L.append(x)
    for w in weights:
        L.append(sigmoid(np.dot(L[-1], w)))
    return L

# backward propagation/ gradient descent
def backProp(error, layers_output, weights, lr=0.01):
    G = [np.zeros(w.shape) for w in weights]
    E = error
    L = layers_output
    
    for i in range(0,len(weights)):
        # calculate the weight delta of the current layer
        G[-(1+i)] = E*sigmoid(L[-(1+i)], derivative=True)
        
        # calculate the error for the next layer backwards
        E = G[-(1+i)].dot(weights[-(1+i)].T)
        
        # update weights
        weights[-(1+i)] += L[-(2+i)].T.dot(G[-(1+i)]) * lr
    
    return G
    


# train the model
n_epochs = 60000

for j in range(n_epochs):
    #feed forward through layers 0,1, and 2
    k0 = x
    k1 = sigmoid(np.dot(k0, W0))
    k2 = sigmoid(np.dot(k1, W1))
    
    #how much did we miss the target value?
    k2_error = y - k2
    
    if (j% 10000) == 0:
        print("Error:" + str(np.mean(np.abs(k2_error))))
    
    #in what direction is the target value?
    k2_delta = k2_error*sigmoid(k2, derivative=True)
    
    #how much did each k1 value contribute to k2 error
    k1_error = k2_delta.dot(W1.T)
    
    k1_delta= k1_error * sigmoid(k1,derivative=True)
    
    W1 += k1.T.dot(k2_delta)
    W0 += k0.T.dot(k1_delta)
    

# use network to predict
x_in = np.array([[1,1,0]])

P = forwardProp(x_in, weights)
print(np.argmax(P[-1]))