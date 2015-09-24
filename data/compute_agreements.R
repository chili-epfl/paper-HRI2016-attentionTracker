
args <- commandArgs(trailingOnly = TRUE)

obs.gt <- read.csv(args[1])
library(irr)
agree(obs.gt[,c("rating1","rating2")])
kappa2(obs.gt[,c("rating1","rating2")])

