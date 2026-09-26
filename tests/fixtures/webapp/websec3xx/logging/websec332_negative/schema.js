const server = new ApolloServer({
  typeDefs,
  resolvers,
  introspection: false,
  validationRules: [depthLimit(5)],
});
