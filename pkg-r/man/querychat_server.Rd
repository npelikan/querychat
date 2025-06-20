% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/querychat.R
\name{querychat_server}
\alias{querychat_server}
\title{Initalize the querychat server}
\usage{
querychat_server(id, querychat_config)
}
\arguments{
\item{id}{The ID of the module instance. Must match the ID passed to
the corresponding call to \code{querychat_ui()}.}

\item{querychat_config}{An object created by \code{querychat_init()}.}
}
\value{
A querychat instance, which is a named list with the following
elements:
\itemize{
\item \code{sql}: A reactive that returns the current SQL query.
\item \code{title}: A reactive that returns the current title.
\item \code{df}: A reactive that returns the filtered data. For data frame sources,
this returns a data.frame. For database sources, this returns a lazy
dbplyr tbl that can be further manipulated with dplyr verbs before
calling collect() to materialize the results.
\item \code{chat}: The \link[ellmer:Chat]{ellmer::Chat} object that powers the chat interface.
}

By convention, this object should be named \code{querychat_config}.
}
\description{
Initalize the querychat server
}
