% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/data_source.R
\name{create_system_prompt}
\alias{create_system_prompt}
\title{Create a system prompt for the data source}
\usage{
create_system_prompt(
  source,
  data_description = NULL,
  extra_instructions = NULL,
  ...
)
}
\arguments{
\item{source}{A querychat_data_source object}

\item{data_description}{Optional description of the data}

\item{extra_instructions}{Optional additional instructions}

\item{...}{Additional arguments passed to methods}
}
\value{
A string with the system prompt
}
\description{
Create a system prompt for the data source
}
