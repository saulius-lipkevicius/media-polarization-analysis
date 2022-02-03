library(data.table)
library(stringr)
library(tm)
library(changepoint)


#  Function takes data and p coefficient as input and returns wordfish estimates
run.wordfish = function(x  #  dataframe   
                        , p  #  p coefficient to remove noise
) {
  #  Find number of documents which is used later to removed rare terms
  ndocs = length(x)
  
  #  Remove every term that is not in at least ndocs*p documents
  dtm = DocumentTermMatrix(x, control = list(bounds = list(global = c(ndocs * p, ndocs))))
  
  #  Convert it to the dfm format
  dfm <- quanteda::as.dfm(dtm)
  
  #  Trim terms that appear less than 5 times in a document, mostly it is mistype trimming
  dfm <- quanteda::dfm_trim(dfm, min_docfreq = 5)
  
  #  Run the model
  mywf <- textmodel_wordfish(dfm, dir = c(1,2))
  
  #  Create a dataframe to test on 
  df.wf = cbind(summary(mywf)[[2]], x[,c("Year", "Media")])
  
  return(df.wf)
}

#  Remove noise and check outliers positioning
remove.noise = function(x  #  dataframe   
     , p  #  p coefficient to remove noise
     , o  #  threshold for outliers
     , i  #  p increasement step size
) {
  #  Run wordfish
  df.wf = run.wordfish(x,p)
  
  #  Find all different medias
  sides = df.wf$Media %>% unique()
  
  #  Separate sides
  df.wf_1 = df.wf %>% filter(Media == sides[1])
  df.wf_2 = df.wf %>% filter(Media == sides[2])
  
  #  Measure how many values are far away from the trend (in opposite side)
  outliers1 = sum(df.wf_1$theta>0)/length(df.wf_1$theta)
  outliers2 = sum(df.wf_2$theta<0)/length(df.wf_2$theta)
  
  #  If more than o% of values are outliers then increase coefficient p and repeat
  if (outliers1 > o | outliers2 > o) {
    if (p == 1) {
    } else {
      p = p + i
    }
  } 
  
  return(p)
}


#  Function removes change points after remove.noise function converge p
remove.changepoints = function(df.wf  #  dataframe   of wordfish results
    , m  #  mean threshold to remove only significantly shifted mean periods
) {
  #  Create vectors for further analyzed data to store
  changepoint.df = NULL
  changepoint.means = NULL
  
  #  Find names for separetion of media
  sides = df.wf$Media %>% unique()
  
  #  Find changepoint measures
  for (media in sides) {
    #  Separate for every media
    df_x = df.wf %>% filter(Media == media)
    
    #  Apply changepoint package to obtain possible shifts in mean or variance
    fit_changepoint = cpt.meanvar(df_x$theta, minseglen=4)
    
    #  Store it
    changepoint.df = c(changepoint.df, cpts(fit_changepoint))
    
    #  Take out mean measures of possible shifter intervals
    fit.means = param.est(fit_changepoint)$mean
    
    #  Measure a shift to later compare it with the threshold
    changepoint.means = c(changepoint.means, fit.means[2] - fit.means[1]) 
  }
  
  #  Find the shortest shift to determine if both sides moved significantly
  chp.min = min(changepoint.df)
  
  #  If one of media didnt have a change-point NA can ruin the flow
  changepoint.means = na.omit(changepoint.means)[1]
  
  #  If the shift is bigger that m value then delete that shift in both sides
  if (max(abs(changepoint.means)) > m & is.null(changepoint.means) == F) {
    #  remove top values of shifter period, multiplied by to to remove both media data
    df.wf = tail(df.wf, -chp.min*2)
  } 
  
  #  Find the lowest date in analyzed period to know what values to filter in the next step
  min.date = min(df.wf$Year)
  return (min.date)
}



#  In step 3 variance is considered to optimize the coefficient p
find.variance = function(df.wf  #  dataframe
                         , m  #  Coefficient p
) {
  #  Run wordfish
  df.wf = run.wordfish(x,p)
  
  #  Detect date when a shift happens
  min.date = remove.changepoints(df.wf,m)
  
  #  Filter everything up to that date
  df.wf = df.wf %>% filter(Year > min.date)
  #  Find all different medias
  sides = mywf$Media %>% unique()
  
  #  Separate sides
  df_1 = df %>% filter(Media == sides[1])
  df_2 = df %>% filter(Media == sides[2])
  
  var1 = var(df_1)
  var2 = var(df_2)
  
  return(c(var1,var2))
}

#  The algorithm
the.method = function(x) {
  
  #  Initial parameters
  p = 0.4
  o = 0.05
  i = 0.02
  m = 0.4
  v = 0.01
  
  #  Step 1, remove the general noise by detecting number of outliers 
  while (p_change > 0) {
    p_new = remove.noise(x  #  Dateframe
                         , p #  Begin with initial p 
                         , o  #  threshold for outliers
                         , i  #  p increasement step size
    ) 
    
    #  Check if p increased
    p_change = p_new - p
    
    #  Set initial p to the new p value
    p = p_new
  }
  
  #  Step 2 find change points for the output
  df.wf = run.wordfish(x,p)
  df.wf_next = run.wordfish(x,p+i)
  min.date = remove.changepoints(df.wf, m)
  
  #  find.variance function has a already in-built function to remove
  #  change points, hence we can care about stability of variance only
  var.change.vector = find.variance(df.wf,m) - find.variance(df.wf_next,m)
  
  #  Run the flow until variance do not stabilizy by more than 0.1
  while (var.change.vector[1] > v & var.change.vector[2] > v) {
    #  Increace p
    p = p + i
    
    #  To find new variance change
    df.wf = run.wordfish(x,p)
    df.wf_next = run.wordfish(x,p+i)
    
    #  Recalculate the variance
    var.change.vector = find.variance(df.wf,m) - find.variance(df.wf_next,m)
  }
  
  #  Run linear regression to give a notice to a user if there is still a trend
  model = lm(theta~Year, data=df.wf)
  
  if (coef(model)[2] > r) {
    print("Topic should be revised and put into subtopics to remove additional noise")
  }
  
  #  Return p value and min.date to filter periods with shifted periods
  return(c(p,min.date))
}