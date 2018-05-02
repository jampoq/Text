from pyspark.sql.types import DoubleType
from pyspark.sql.functions import lit, udf, coalesce
import utils

##############
# Pipeline
##############

class Pipeline():

    def __init__(self, pyspark_df,spark_session):
        self.df = pyspark_df
        self.session = spark_session

    def add_helpful_col(self):
        '''
        Takes in a pyspark dataframe and returns a dataframe with
        the helpfulness columns added.

        Input:
        --------
        None

        Output:
        --------
        None
        '''

        # Creates two new columns from the helpful column.
        self.df = self.df.withColumn('review_count',utils.ith('helpful',lit(1))) \
                         .withColumn('helpful_count',utils.ith('helpful',lit(0)))

    def filter_helpful(self,n):
        '''
        Filter for all reviews where it's been tagged at least
        n times.

        Input:
        --------
        n : How many minimum tags the review has
        Output:
        --------
        None
        '''
        self.add_helpful_col()
        self.df = self.df.filter(self.df['review_count'] >= n) \
                         .withColumn('helpfulness',coalesce(self.df['helpful_count']/self.df['review_count'],lit(0)))

    def get_data(self,n,threshold):
        '''
        Get data to add features to and put into models.

        Input:
        --------
        n : How many minum tages the review has
        threshold : ratio of helpful not helpful you want

        Output:
        --------
        None
        '''
        self.filter_helpful(n)

        # Store dataframe into temp table
        self.df.registerTempTable('reviews')

        # Spark dataframe that will get vectorized and put in a model.
        self.df = self.session.sql("""select
                                      reviewerID,
                                      overall,
                                      reviewText,
                                      unixReviewTime,
                                      case when helpfulness >= {thresh} then 1
                                           else 0
                                      end as label
                                      from reviews
                               """.format(thresh = str(threshold)))

        return self.df

    def add_first_layer_features(self):
        '''
        Add first layer of features using the udf functions from util.py.

        Input:
        -------
        None

        Output:
        -------
        None
        '''
        self.df = self.df.withColumn('sentence_cnt',utils.sentence_count(self.df.reviewText)) \
                         .withColumn('word_cnt',utils.word_count(self.df.reviewText)) \
                         .withColumn('capital_cnt',utils.count_capital(self.df.reviewText)) \
                         .withColumn('upper_word_cnt',utils.all_caps(self.df.reviewText)) \
                         .withColumn('punctuation_cnt',utils.count_punctuation(self.df.reviewText)) \
                         .withColumn('overall_transform',utils.overall_transform(self.df.overall))

    def add_sec_layer_features(self):
        '''
        Add second layer of features using features from the first layer.

        Input:
        -------
        None

        Output:
        -------
        None
        '''
        self.df = self.df.withColumn('avg_word_cnt',self.df.word_cnt/self.df.sentence_cnt) \
                         .withColumn('avg_punc_cnt',self.df.punctuation_cnt/self.df.sentence_cnt) \
                         .withColumn('avg_capital_cnt',self.df.capital_cnt/self.df.sentence_cnt) \
                         .withColumn('avg_upper_cnt',self.df.upper_word_cnt/self.df.sentence_cnt)
