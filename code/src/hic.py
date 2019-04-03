"""
.. module:: Hic
   :synopsis: This module implements the Hic class.
"""

# Third-party modules
import math as m
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable


class Hic:
    """
    .. class:: Hic
        This class groups informations about a Hi-C matrix.

    Attributes:
        cooler (cooler): Storage of the Hi-C matrix
        resolution (int): Resolution (or bin-size) of the Hi-C matrix
        chrom (int): Chromosome chosen among all chromosomes in cooler
        side (int): Number of raws and columns of a numpy array sub-matrix
        matrix (numpy array): Hi-C matrix of the chromosome chosen stored in a numpy array
        sub_matrices (numpy array): The splitted Hi-C matrix into N sub-matrices of size side*side
                                    stored in a numpy array of shape (Samples, side, side, 1)
    """

    def __init__(self, cooler, chrom, square_side):
        self.cooler = cooler
        self.resolution = self.cooler.info['bin-size']
        self.chrom = chrom
        self.side = square_side
        self.matrix = None
        self.sub_matrices = None

    def calculate_cum_length(self):
        """
            Calculates and returns the cumulated length from chromosome 1 to N.
        """
        chroms = self.cooler.chroms()[:]
        cum_length = []
        for i, size in enumerate(list(chroms.length)):
            if i == 0:
                cum_length.append(size)
            else:
                cum_length.append(size + cum_length[i-1])
        chroms['cum_length'] = cum_length
        return chroms

    def set_matrix(self):
        """
            Set the numpy array Hi-C matrix of the chromosome chrom.
            The matrix is transformed into an upper triangular matrix and the values are converted
            in float32, rescaled by log10 and normalized.
        """
        chroms = self.calculate_cum_length()
        if self.chrom == 1:
            bin_1 = 0
        else:
            bin_1 = m.ceil(chroms[self.chrom-2:self.chrom-1]['cum_length']/self.resolution)
        bin_2 = m.ceil(chroms[self.chrom-1:self.chrom]['cum_length']/self.resolution)
        # Creation of the sparse matrix and conversion into a numpy array
        matrix = self.cooler.matrix(balance=False, sparse=True)[bin_1:bin_2, bin_1:bin_2].toarray()
        ## 0s are interpreted as missing values by Keras
        # matrix = matrix + 1
        # The matrix is symetric then we keep only the upper triangular matrix
        matrix = np.triu(matrix)
        # Conversion into float32
        matrix = np.float32(matrix)
        # Log scale to visualize better the matrix in plot
        matrix = np.log10(matrix+1)
        # Rescaling of the values in range 0-1
        # (min-max scaling method)
        matrix = (matrix - matrix.min()) / (matrix.max() - matrix.min())
        # # Lines are removing or added (0s)
        # if lines < 0:
        #     matrix = matrix[abs(lines):, abs(lines):]
        # elif lines > 0
        #     matrix = np.insert(matrix, 0, 0, axis = 0)
        #     matrix = np.insert(matrix, 0, 0, axis = 1)
        self.matrix = matrix

    def set_sub_matrices(self):
        """
            Split the Hi-C matrix of the chromosome chrom into N sub-matrices of size side*side.
            The empty sub-matrices (sum(values)==0) are ignored.
            The N resulted sub-matrices are stored and set in a numpy array
            of shape (N, side, side, 1).
        """
        sub_matrices_list = []
        for i in range(0, self.matrix.shape[1], self.side):
            for j in range(0, self.matrix.shape[1], self.side):
                sub_matrix = self.matrix[i:i+self.side, j:j+self.side]
                # We do not want sub-matrix with a size different than side*side
                if sub_matrix.shape != (self.side, self.side):
                    break
                # The empty sub-matrices are not taking into account
                if sub_matrix.sum() != 0:
                    sub_matrices_list.append(sub_matrix)
        sub_matrices = np.array(sub_matrices_list)
        # The number of sub-matrices is calculated automatically by using -1 in the first field
        sub_matrices = sub_matrices.reshape(-1, self.side, self.side, 1)
        self.sub_matrices = sub_matrices

    def plot_ten_sub_matrices(self, color_map, output_path, index_list):
        """
            10 sub-matrices are plotted in a file.
        """
        plt.figure(figsize=(18, 2))
        for i, index in enumerate(index_list):
            plt.subplot(1, 10, i+1)
            plt.imshow(self.sub_matrices[index, ..., 0], cmap=color_map)
            plt.title("submatrix n°{}".format(index))
        plt.subplots_adjust(left=0.03, right=0.98, wspace=0.3)
        plt.savefig('{}/10submatrices_chr{}_true.png'.format(output_path, self.chrom))

    def plot_matrix(self, color_map, output_path):
        """
            The Hi-C matrix is plotted in a file. 
        """
        fig = plt.figure(figsize=(12, 12))
        axes = plt.subplot(111, aspect='equal')
        img = axes.matshow(self.matrix, cmap=color_map)
        divider = make_axes_locatable(axes)
        cax = divider.append_axes("right", size="2%", pad=0.15)
        plt.colorbar(img, cax=cax)
        plt.subplots_adjust(left=0.07, bottom=0, right=0.95, top=0.91, wspace=0, hspace=0)
        axes.set_title('True chr{} Hi-C matrix'.format(self.chrom), fontsize=25)
        fig.savefig('{}/chr{}_true.png'.format(output_path, self.chrom))
