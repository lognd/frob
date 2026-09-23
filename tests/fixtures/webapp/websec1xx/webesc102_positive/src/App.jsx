export function Comment({ userHtml }) {
  return <div dangerouslySetInnerHTML={{ __html: userHtml }} />;
}
