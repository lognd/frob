import Head from "next/head";

export default function Product() {
  return (
    <Head>
      <title>Widget Pro</title>
      <meta name="description" content="The best widget" />
      <link rel="canonical" href="https://acme.example/product" />
      <script type="application/ld+json">{"a":1}</script>
    </Head>
  );
}
