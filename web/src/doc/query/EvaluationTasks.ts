const QUERY = /* GraphQL */ `
  query EvaluationTasks {
    currentUser {
      evaluationTasks {
        id
        name
        status
        points
        createdAt
      }
    }
  }
`
export default QUERY
